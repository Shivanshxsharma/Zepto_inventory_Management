"""
04_purchase_orders.py -- Generate supply/restocks first.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATASET_DIR, get_store_demand_weights

np.random.seed(42)

# Load data
products = pd.read_csv(os.path.join(DATASET_DIR, "products.csv"), encoding="utf-8-sig")
stores = pd.read_csv(os.path.join(DATASET_DIR, "dark_stores.csv"), encoding="utf-8-sig")
prod_sup = pd.read_csv(os.path.join(DATASET_DIR, "product_suppliers.csv"), encoding="utf-8-sig")
suppliers_df = pd.read_csv(os.path.join(DATASET_DIR, "suppliers.csv"), encoding="utf-8-sig")

# Lookups
store_ids = stores["store_id"].values

store_discipline = {}
store_id_list = list(store_ids)
tight_stores = set(np.random.choice(
    store_id_list, size=len(store_id_list)//2, replace=False
))
for sid in store_id_list:
    if sid in tight_stores:
        store_discipline[sid] = (0.93, 0.97)
    else:
        store_discipline[sid] = (0.98, 1.04)

# Category-level oversupply biases: perishables get a small safety buffer
# (they expire fast so stores slightly over-order to prevent stockouts),
# while long-shelf-life items are ordered precisely to demand.
category_oversupply_bias = {
    'Fruits & Vegetables':   1.01,
    'Dairy, Bread & Batter': 1.01,
    'Meats, Fish & Eggs':    1.03,
    'Beverages':             1.00,
    'Ice Cream & Desserts':  1.02,
    'Paan Corner':           1.02,
}

sup_lead = dict(zip(suppliers_df["supplier_id"], suppliers_df["avg_lead_time_days"]))
store_demand_weights = get_store_demand_weights(DATASET_DIR)

sku_suppliers = {}
for _, row in prod_sup.iterrows():
    sku_suppliers.setdefault(int(row["sku_id"]), []).append(
        (int(row["supplier_id"]), float(row["cost_price"]))
    )

start_date = datetime(2025, 1, 1)
num_days = 90

po_rows = []
batch_id_counter = 0
po_line_id_counter = 0
on_time_count = 0
late_count = 0

print("Generating opening stock (December 2024)...")
# ==========================================
# 1. OPENING STOCK GENERATION
# ==========================================
opening_stock_batches_created = 0
opening_stock_qty_total = 0
store_sku_covered = 0

# To satisfy the requirement: "one batch per unique (store_id, supplier_id) pair"
opening_batch_lookup = {}

for sid in store_ids:
    for _, prod in products.iterrows():
        sku = int(prod["sku_id"])
        dw = int(prod["demand_weight"])
        
        if sku not in sku_suppliers:
            continue
            
        avg_daily_demand = dw * 0.10 * store_demand_weights.get(sid, 1.0)
        opening_qty = int(round(avg_daily_demand * np.random.uniform(7, 11)))
        
        if opening_qty <= 0:
            continue
            
        # Pick a supplier
        sup_idx = np.random.randint(len(sku_suppliers[sku]))
        sup_id, cost_price = sku_suppliers[sku][sup_idx]
        
        # Determine the batch_id
        if (sid, sup_id) not in opening_batch_lookup:
            batch_id_counter += 1
            opening_batch_lookup[(sid, sup_id)] = batch_id_counter
            opening_stock_batches_created += 1
            
        current_batch = opening_batch_lookup[(sid, sup_id)]
        
        po_line_id_counter += 1
        po_line_id_str = f"OPEN-{po_line_id_counter}"
        
        po_rows.append({
            "batch_id": current_batch,
            "po_line_id": po_line_id_str,
            "store_id": sid,
            "sku_id": sku,
            "supplier_id": sup_id,
            "order_date": "2024-12-05",
            "expected_delivery_date": "2024-12-12",
            "actual_delivery_date": "2024-12-12",
            "quantity_ordered": opening_qty,
            "cost_price": cost_price
        })
        
        opening_stock_qty_total += opening_qty
        store_sku_covered += 1
        on_time_count += 1

print(f"  - Total opening quantity generated: {opening_stock_qty_total:,}")
print(f"  - Number of store-SKU pairs covered: {store_sku_covered:,}")
print(f"  - Number of batches created: {opening_stock_batches_created:,}")

# Check coverage: every SKU with demand_weight > 0 should have an opening stock row for every store
target_coverage = len(store_ids) * len(products[products['demand_weight'] > 0])
if store_sku_covered < target_coverage:
    print(f"  - Note: Only covered {store_sku_covered} / {target_coverage} possible store-SKU pairs (due to random generation yielding 0).")
else:
    print(f"  - Note: Covered all expected {target_coverage} store-SKU pairs.")


print("\nGenerating purchase orders based on projected demand (2025)...")
# ==========================================
# 2. REPLENISHMENT GENERATION (2025)
# ==========================================
# The user asked: "change the existing batch_id assignment logic (grouping by store_id, supplier_id, actual_delivery_date, from our earlier fix) so its counter starts after the highest opening-stock batch_id"

replenishment_batch_lookup = {}
po_line_id_replenishment_counter = 0

for sid in store_ids:
    for _, prod in products.iterrows():
        sku = int(prod["sku_id"])
        dw = int(prod["demand_weight"])
        
        if sku not in sku_suppliers:
            continue
            
        avg_daily_demand = dw * 0.10 * store_demand_weights.get(sid, 1.0)
        # 64 weekdays (1.0x) + 26 weekend days (1.6x avg) = 105.6x daily demand for 90 days
        expected_monthly_demand = avg_daily_demand * 105.6
        
        lo, hi = store_discipline[sid]
        cat_bias = category_oversupply_bias.get(prod["category"], 1.0)
        target_monthly_supply = expected_monthly_demand * np.random.uniform(lo, hi) * cat_bias
        target_qty = int(round(target_monthly_supply))
        
        if target_qty <= 0:
            if np.random.random() < 0.2:
                target_qty = 1
            else:
                continue
                
        # High-frequency JIT deliveries to keep on-hand inventory low.
        # Perishables get near-daily deliveries; non-perishables still get frequent small batches.
        if prod["category"] == "Meats, Fish & Eggs":
            num_pos = np.random.randint(20, 30)
        elif prod["category"] in ("Fruits & Vegetables", "Dairy, Bread & Batter", "Paan Corner"):
            num_pos = np.random.randint(15, 22)
        elif dw >= 8:
            num_pos = np.random.randint(12, 18)
        elif dw >= 5:
            num_pos = np.random.randint(9, 13)
        elif dw >= 3:
            num_pos = np.random.randint(6, 10)
        else:
            num_pos = np.random.randint(3, 6)
            
        if num_pos > target_qty:
            num_pos = target_qty
            
        base_qty = target_qty // num_pos
        remainder = target_qty % num_pos
        
        order_days = np.sort(np.random.choice(num_days, size=num_pos, replace=False))
        
        for i, od_offset in enumerate(order_days):
            sup_idx = np.random.randint(len(sku_suppliers[sku]))
            sup_id, cost_price = sku_suppliers[sku][sup_idx]
            lead_time = sup_lead.get(sup_id, 3)
            
            order_date = start_date + timedelta(days=int(od_offset))
            expected_delivery = order_date + timedelta(days=lead_time)
            
            is_late = np.random.random() < 0.15
            if is_late:
                late_days = np.random.randint(1, 4)
                actual_delivery = expected_delivery + timedelta(days=late_days)
                late_count += 1
            else:
                actual_delivery = expected_delivery
                on_time_count += 1
                
            qty = base_qty + (1 if i < remainder else 0)
            if qty <= 0:
                continue
                
            actual_delivery_str = actual_delivery.strftime("%Y-%m-%d")
            
            if (sid, sup_id, actual_delivery_str) not in replenishment_batch_lookup:
                batch_id_counter += 1
                replenishment_batch_lookup[(sid, sup_id, actual_delivery_str)] = batch_id_counter
                
            current_batch = replenishment_batch_lookup[(sid, sup_id, actual_delivery_str)]
            
            po_line_id_replenishment_counter += 1
            po_line_id_str = f"PO-{po_line_id_replenishment_counter}"
                
            po_rows.append({
                "batch_id": current_batch,
                "po_line_id": po_line_id_str,
                "store_id": sid,
                "sku_id": sku,
                "supplier_id": sup_id,
                "order_date": order_date.strftime("%Y-%m-%d"),
                "expected_delivery_date": expected_delivery.strftime("%Y-%m-%d"),
                "actual_delivery_date": actual_delivery_str,
                "quantity_ordered": qty,
                "cost_price": cost_price
            })

po_df = pd.DataFrame(po_rows)
out_path = os.path.join(DATASET_DIR, "purchase_orders.csv")
print("Saved purchase_orders.csv.")

print(f"\nStore discipline assignment:")
print(f"  Tight (low-waste) stores: {sorted(tight_stores)}")
print(f"  Loose (moderate-waste) stores: {sorted(set(store_id_list) - tight_stores)}")
po_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print("\n=== STEP 1: PURCHASE ORDERS VALIDATION ===")
print(f"Total Rows Generated:     {len(po_df):,}")
print(f"Total Quantity Ordered:   {po_df['quantity_ordered'].sum():,}")
print(f"On-Time Deliveries:       {on_time_count:,} ({(on_time_count/(on_time_count+late_count))*100:.1f}%)")
print(f"Late Deliveries:          {late_count:,} ({(late_count/(on_time_count+late_count))*100:.1f}%)")
print(f"Saved -> {out_path}")
