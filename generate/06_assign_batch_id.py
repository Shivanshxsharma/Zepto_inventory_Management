import pandas as pd
import os
import sys

def main():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')
    
    # Load data
    print("Loading data...")
    try:
        products_df = pd.read_csv(os.path.join(base_dir, 'products.csv'))
        po_df = pd.read_csv(os.path.join(base_dir, 'purchase_orders.csv'))
        orders_df = pd.read_csv(os.path.join(base_dir, 'orders.csv'))
        order_items_df = pd.read_csv(os.path.join(base_dir, 'order_items.csv'))
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)

    # 2. Process order_items
    print("Processing order items...")
    
    po_df['actual_delivery_date'] = pd.to_datetime(po_df['actual_delivery_date'])
    products_df['shelf_life_days'] = pd.to_timedelta(products_df['shelf_life_days'], unit='D')
    po_merged = po_df.merge(products_df[['sku_id', 'shelf_life_days']], on='sku_id', how='left')
    po_merged['expiry_date'] = po_merged['actual_delivery_date'] + po_merged['shelf_life_days']

    orders_df['order_timestamp'] = pd.to_datetime(orders_df['order_timestamp'])
    orders_df['order_date'] = orders_df['order_timestamp'].dt.normalize()
    
    # Identify cancelled items so we don't count them as anomalies if they don't get a batch_id
    items_with_orders = order_items_df.merge(
        orders_df[['order_id', 'store_id', 'order_timestamp', 'order_date', 'order_status']], 
        on='order_id', 
        how='left'
    )
    
    # Filter out cancelled
    items_to_process = items_with_orders[items_with_orders['order_status'] != 'cancelled'].copy()
    items_to_process = items_to_process.sort_values('order_timestamp')

    order_items_df['batch_id'] = pd.NA
    
    anomalies = []
    success_count = 0
    split_count = 0
    total_to_process = len(items_to_process)
    
    sample_traces = []
    sample_count = 0

    batch_assignments = {}

    # Optimization: pre-calculate everything into dicts for faster iteration inside groups
    # Group by store_id and sku_id
    grouped_items = items_to_process.groupby(['store_id', 'sku_id'])
    
    for (store_id, sku_id), group_items in grouped_items:
        group_po = po_merged[(po_merged['store_id'] == store_id) & (po_merged['sku_id'] == sku_id)].copy()
        group_po = group_po.sort_values('actual_delivery_date')
        
        batches = group_po.to_dict('records')
        for b in batches:
            b['remaining_qty'] = b['quantity_ordered']
            
        batch_idx = 0
        open_batches = []
        
        trace = []
        is_sample = sample_count < 3 and len(group_items) > 0
        
        # Iterate over sales chronologically
        for item in group_items.to_dict('records'):
            sale_date = item['order_date']
            
            # 1. Add batches that have arrived by this sale_date
            while batch_idx < len(batches) and batches[batch_idx]['actual_delivery_date'] <= sale_date:
                open_batches.append(batches[batch_idx])
                if is_sample:
                    trace.append(f"-> ARRIVED: Batch {batches[batch_idx]['batch_id']} on {batches[batch_idx]['actual_delivery_date'].date()} with {batches[batch_idx]['quantity_ordered']} qty. (Expires: {batches[batch_idx]['expiry_date'].date()})")
                batch_idx += 1
                
            # 2. Prune expired batches
            valid_batches = []
            for b in open_batches:
                if b['expiry_date'] >= sale_date:
                    valid_batches.append(b)
                else:
                    if is_sample:
                        trace.append(f"-> EXPIRED: Batch {b['batch_id']} on {b['expiry_date'].date()} with {b['remaining_qty']} qty remaining. (Sale date is {sale_date.date()})")
            open_batches = valid_batches
            
            qty_needed = item['quantity']
            batch_contributions = {}
            
            # 3. Fulfill from oldest valid batches
            for b in open_batches:
                if qty_needed == 0:
                    break
                if b['remaining_qty'] > 0:
                    take = min(b['remaining_qty'], qty_needed)
                    b['remaining_qty'] -= take
                    qty_needed -= take
                    batch_contributions[b['batch_id']] = take
                    
            if qty_needed > 0:
                # Could not fully fulfill
                anomalies.append(item)
            else:
                # Successfully fulfilled, find batch with max contribution
                best_batch_id = max(batch_contributions.items(), key=lambda x: x[1])[0]
                # Update our dictionary
                batch_assignments[item['order_item_id']] = best_batch_id

                    
                if len(batch_contributions) > 1:
                    split_count += 1
                    
                success_count += 1
                if is_sample:
                    trace.append(f"-> SALE: Item ID {item['order_item_id']} on {sale_date.date()} for qty {item['quantity']} -> Assigned to Batch {best_batch_id}")
                    if len(batch_contributions) > 1:
                        trace.append(f"   (Split fulfillment: {batch_contributions})")
                        
        if is_sample:
            sample_traces.append((store_id, sku_id, trace))
            sample_count += 1
            
    # Apply assignments using mapping (O(N) operation instead of O(N^2))
    print("Applying batch assignments...")
    order_items_df['batch_id'] = order_items_df['order_item_id'].map(batch_assignments)

    # Save output
    order_items_df.to_csv(os.path.join(base_dir, 'order_items.csv'), index=False)
    print("Appended batch_id to order_items.csv and saved.")

    
    # 3. Validation Summary
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    print(f"Total non-cancelled order_items processed: {total_to_process}")
    
    success_rate = (success_count / total_to_process) * 100 if total_to_process > 0 else 0
    print(f"Items successfully assigned a batch_id: {success_count} ({success_rate:.2f}%)")
    
    split_rate = (split_count / success_count) * 100 if success_count > 0 else 0
    print(f"Items fulfilled from multiple batches (splits): {split_count} ({split_rate:.2f}% of successes)")
    
    anomaly_rate = (len(anomalies) / total_to_process) * 100 if total_to_process > 0 else 0
    print(f"\nAnomalies (could not match stock): {len(anomalies)} ({anomaly_rate:.2f}%)")
    if len(anomalies) > 0:
        print("Sample of anomalies:")
        for a in anomalies[:5]:
            print(f"  - Order Item ID: {a['order_item_id']}, SKU: {a['sku_id']}, Store: {a['store_id']}, Qty needed: {a['quantity']}, Order Date: {a['order_date'].date()}")
            
    print("\n" + "="*50)
    print("FIFO LOGIC VERIFICATION (3 SAMPLES)")
    print("="*50)
    for s_id, sk_id, trace in sample_traces:
        print(f"\n--- Store {s_id}, SKU {sk_id} ---")
        if not trace:
            print("  No transactions.")
        for t in trace:
            print(f"  {t}")
            
if __name__ == "__main__":
    main()
