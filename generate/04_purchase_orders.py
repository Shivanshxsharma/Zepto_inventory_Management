"""
04_purchase_orders.py -- Generate supply/restocks first.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATASET_DIR

np.random.seed(42)

# Load data
products = pd.read_csv(os.path.join(DATASET_DIR, "products.csv"), encoding="utf-8-sig")
stores = pd.read_csv(os.path.join(DATASET_DIR, "dark_stores.csv"), encoding="utf-8-sig")
prod_sup = pd.read_csv(os.path.join(DATASET_DIR, "product_suppliers.csv"), encoding="utf-8-sig")
suppliers_df = pd.read_csv(os.path.join(DATASET_DIR, "suppliers.csv"), encoding="utf-8-sig")

# Lookups
store_ids = stores["store_id"].values
sup_lead = dict(zip(suppliers_df["supplier_id"], suppliers_df["avg_lead_time_days"]))

sku_suppliers = {}
for _, row in prod_sup.iterrows():
    sku_suppliers.setdefault(int(row["sku_id"]), []).append(
        (int(row["supplier_id"]), float(row["cost_price"]))
    )

start_date = datetime(2025, 1, 1)
num_days = 31

po_rows = []
po_id = 0
on_time_count = 0
late_count = 0

print("Generating purchase orders based on projected demand...")

for sid in store_ids:
    for _, prod in products.iterrows():
        sku = int(prod["sku_id"])
        dw = int(prod["demand_weight"])
        
        if sku not in sku_suppliers:
            continue
            
        # Demand estimation base (must match 05_orders.py)
        avg_daily_demand = dw * 0.035
        expected_monthly_demand = avg_daily_demand * num_days
        
        # Target supply (1.1x to 1.4x of expected demand)
        # Random uniform multiplier so some SKUs might run tight (closer to 1.0 or 1.1)
        target_monthly_supply = expected_monthly_demand * np.random.uniform(1.1, 1.4)
        target_qty = int(round(target_monthly_supply))
        
        if target_qty <= 0:
            # For extremely low demand SKUs, maybe order 1 unit occasionally
            if np.random.random() < 0.2:
                target_qty = 1
            else:
                continue
                
        # Determine frequency (number of POs in the month)
        if dw >= 8:
            num_pos = np.random.randint(4, 7)  # More frequent
        elif dw >= 5:
            num_pos = np.random.randint(3, 5)
        elif dw >= 3:
            num_pos = np.random.randint(2, 4)
        else:
            num_pos = np.random.randint(1, 3)  # Less frequent
            
        if num_pos > target_qty:
            num_pos = target_qty
            
        # Distribute the target_qty evenly across orders
        base_qty = target_qty // num_pos
        remainder = target_qty % num_pos
        
        # Determine random order dates across the 31 days
        order_days = np.sort(np.random.choice(num_days, size=num_pos, replace=False))
        
        for i, od_offset in enumerate(order_days):
            po_id += 1
            
            # Pick a supplier
            sup_idx = np.random.randint(len(sku_suppliers[sku]))
            sup_id, cost_price = sku_suppliers[sku][sup_idx]
            lead_time = sup_lead.get(sup_id, 3)
            
            order_date = start_date + timedelta(days=int(od_offset))
            expected_delivery = order_date + timedelta(days=lead_time)
            
            # ~85% on time, ~15% arrive 1-3 days late
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
                
            po_rows.append({
                "po_id": po_id,
                "store_id": sid,
                "sku_id": sku,
                "supplier_id": sup_id,
                "order_date": order_date.strftime("%Y-%m-%d"),
                "expected_delivery_date": expected_delivery.strftime("%Y-%m-%d"),
                "actual_delivery_date": actual_delivery.strftime("%Y-%m-%d"),
                "quantity_ordered": qty,
                "cost_price": cost_price
            })

po_df = pd.DataFrame(po_rows)
out_path = os.path.join(DATASET_DIR, "purchase_orders.csv")
po_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print("\n=== STEP 1: PURCHASE ORDERS VALIDATION ===")
print(f"Total Rows Generated:     {len(po_df):,}")
print(f"Total Quantity Ordered:   {po_df['quantity_ordered'].sum():,}")
print(f"On-Time Deliveries:       {on_time_count:,} ({(on_time_count/(on_time_count+late_count))*100:.1f}%)")
print(f"Late Deliveries:          {late_count:,} ({(late_count/(on_time_count+late_count))*100:.1f}%)")
print(f"Saved -> {out_path}")
