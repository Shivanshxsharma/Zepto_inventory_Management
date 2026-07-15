"""
05_orders.py -- Generate orders sequentially checking against available stock.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATASET_DIR, NUM_CUSTOMERS

np.random.seed(42)

# 1. Load Data
products = pd.read_csv(os.path.join(DATASET_DIR, "products.csv"), encoding="utf-8-sig")
stores = pd.read_csv(os.path.join(DATASET_DIR, "dark_stores.csv"), encoding="utf-8-sig")
pos = pd.read_csv(os.path.join(DATASET_DIR, "purchase_orders.csv"), encoding="utf-8-sig")
customers = pd.read_csv(os.path.join(DATASET_DIR, "customers.csv"), encoding="utf-8-sig")

# Lookups
store_ids = stores["store_id"].values
store_zones = dict(zip(stores["store_id"], stores["zone"]))
sku_mrps = dict(zip(products["sku_id"], products["mrp"]))
sku_demand_weights = dict(zip(products["sku_id"], products["demand_weight"]))

cust_by_zone = {}
for zone in customers["zone"].unique():
    cust_by_zone[zone] = customers[customers["zone"] == zone]["customer_id"].values
all_cust_ids = customers["customer_id"].values

start_date = datetime(2025, 1, 1)
num_days = 31
dates = [start_date + timedelta(days=i) for i in range(num_days)]
date_strs = [d.strftime("%Y-%m-%d") for d in dates]
is_weekend = [d.weekday() >= 5 for d in dates]

# 2. Pre-process POs to daily received quantities
pos_delivered = pos[pos["actual_delivery_date"].notna()].copy()
received_agg = pos_delivered.groupby(["store_id", "sku_id", "actual_delivery_date"])["quantity_ordered"].sum().to_dict()

daily_sold_records = []
total_stockouts = 0
total_store_sku_days = 0

sample_traces = []
sample_pairs = [(1, 1), (2, 5), (3, 10)]

print("Simulating daily sales against inventory constraints...")

for sid in store_ids:
    for sku in products["sku_id"].values:
        dw = sku_demand_weights[sku]
        avg_daily_demand = dw * 0.035
        
        # Seed inventory
        available_stock = int(round(avg_daily_demand * np.random.uniform(15, 20)))
        
        trace = []
        is_sample = (sid, sku) in sample_pairs
        
        for i, d_str in enumerate(date_strs):
            total_store_sku_days += 1
            
            # a. Receive stock
            received_qty = received_agg.get((sid, sku, d_str), 0)
            before_stock = available_stock
            available_stock += received_qty
            
            # b. Demand
            mult = np.random.uniform(1.4, 1.8) if is_weekend[i] else 1.0
            lambda_demand = avg_daily_demand * mult
            quantity_wanted = np.random.poisson(lambda_demand)
            
            # c. Sell
            quantity_sold = min(quantity_wanted, available_stock)
            
            if quantity_wanted > available_stock:
                total_stockouts += 1
                
            # d. Update stock
            available_stock -= quantity_sold
            
            if is_sample:
                trace.append({
                    "date": d_str,
                    "before": before_stock,
                    "received": received_qty,
                    "wanted": quantity_wanted,
                    "sold": quantity_sold,
                    "after": available_stock
                })
                
            if quantity_sold > 0:
                daily_sold_records.append({
                    "store_id": sid,
                    "date": d_str,
                    "sku_id": sku,
                    "qty": quantity_sold
                })
                
        if is_sample:
            sample_traces.append((sid, sku, trace))


print("Reconstructing individual customer orders...")
sold_df = pd.DataFrame(daily_sold_records)

HOUR_WEIGHTS = np.array([
    1, 1, 1, 1, 1, 1,
    3, 5, 7, 8, 8, 6,
    5, 5, 4, 4, 5, 7,
    10, 12, 11, 8, 5, 3
], dtype=float)
HOUR_PROBS = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()
HOURS = np.arange(24)

orders = []
order_items = []
order_id = 0
item_id = 0

def gen_delivery_time():
    t = np.random.lognormal(mean=np.log(18), sigma=0.35)
    return int(np.clip(round(t), 10, 45))

if not sold_df.empty:
    grouped = sold_df.groupby(["store_id", "date"])
    
    for (sid, d_str), group in grouped:
        s_zone = store_zones[sid]
        z_custs = cust_by_zone.get(s_zone, all_cust_ids)
        
        pool_skus = []
        for _, row in group.iterrows():
            pool_skus.extend([row["sku_id"]] * row["qty"])
            
        np.random.shuffle(pool_skus)
        
        pool_idx = 0
        total_pool = len(pool_skus)
        
        # We generate the DELIVERED orders from the pool
        while pool_idx < total_pool:
            order_id += 1
            n_items = min(np.random.choice([1, 2, 3, 4, 5, 6], p=[0.25, 0.30, 0.20, 0.12, 0.08, 0.05]), total_pool - pool_idx)
            order_skus = pool_skus[pool_idx : pool_idx + n_items]
            pool_idx += n_items
            
            c_id = np.random.choice(z_custs) if np.random.random() < 0.8 else np.random.choice(all_cust_ids)
                
            hr = np.random.choice(HOURS, p=HOUR_PROBS)
            mn = np.random.randint(0, 60)
            sc = np.random.randint(0, 60)
            ts = f"{d_str} {hr:02d}:{mn:02d}:{sc:02d}"
            
            del_time = gen_delivery_time()
            
            orders.append({
                "order_id": order_id,
                "customer_id": c_id,
                "store_id": sid,
                "order_timestamp": ts,
                "order_status": "delivered",
                "delivery_time_mins": del_time
            })
            
            from collections import Counter
            sku_counts = Counter(order_skus)
            
            for o_sku, o_qty in sku_counts.items():
                item_id += 1
                mrp = sku_mrps[o_sku]
                discount = np.random.choice([0, 5, 10, 15, 20], p=[0.4, 0.2, 0.2, 0.12, 0.08])
                unit_price = round(mrp * (1 - discount / 100), 2)
                
                order_items.append({
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "sku_id": o_sku,
                    "quantity": o_qty,
                    "unit_price_at_sale": unit_price,
                    "discount_pct": discount
                })
        
        # Now generate a ~4% extra batch of CANCELLED orders. 
        # Since they are cancelled, they never permanently depleted available_stock.
        # This elegantly solves the requirement without complex mid-loop stock add-backs.
        num_cancelled = int(np.ceil((order_id * 0.04) / 31)) # Rough daily amount per store
        if num_cancelled > 0:
            for _ in range(num_cancelled):
                order_id += 1
                c_id = np.random.choice(z_custs) if np.random.random() < 0.8 else np.random.choice(all_cust_ids)
                
                hr = np.random.choice(HOURS, p=HOUR_PROBS)
                ts = f"{d_str} {hr:02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}"
                
                orders.append({
                    "order_id": order_id,
                    "customer_id": c_id,
                    "store_id": sid,
                    "order_timestamp": ts,
                    "order_status": "cancelled",
                    "delivery_time_mins": ""
                })
                
                n_items = np.random.randint(1, 4)
                rand_skus = np.random.choice(products["sku_id"].values, size=n_items)
                
                for o_sku in rand_skus:
                    item_id += 1
                    mrp = sku_mrps[o_sku]
                    order_items.append({
                        "order_item_id": item_id,
                        "order_id": order_id,
                        "sku_id": o_sku,
                        "quantity": np.random.randint(1, 3),
                        "unit_price_at_sale": mrp,
                        "discount_pct": 0
                    })


# 3. Output
orders_df = pd.DataFrame(orders)
orders_path = os.path.join(DATASET_DIR, "orders.csv")
orders_df.to_csv(orders_path, index=False, encoding="utf-8-sig")

items_df = pd.DataFrame(order_items)
items_path = os.path.join(DATASET_DIR, "order_items.csv")
items_df.to_csv(items_path, index=False, encoding="utf-8-sig")

print("\n=== STEP 2: VALIDATION CHECKS ===")
print("Constraint Check: cumulative sold <= cumulative purchased (TRUE by sequential clamp).")
print(f"Total Row Count - orders.csv:      {len(orders_df):,}")
print(f"Total Row Count - order_items.csv: {len(items_df):,}  (Target: 150k-300k)")

stockout_rate = (total_stockouts / total_store_sku_days) * 100 if total_store_sku_days else 0
print(f"Stockout Rate: {stockout_rate:.2f}% of store-sku-days had unmet demand.")

print("\nSample Traces (Store, SKU):")
for sid, sku, trace in sample_traces:
    print(f"\n--- Store {sid}, SKU {sku} ---")
    if len(trace) > 0:
        for row in trace[:4]:
            print(f"  {row['date']} | Start: {row['before']} | Recv: {row['received']} | Want: {row['wanted']} | Sold: {row['sold']} | End: {row['after']}")
        print("  ...")
        for row in trace[-2:]:
            print(f"  {row['date']} | Start: {row['before']} | Recv: {row['received']} | Want: {row['wanted']} | Sold: {row['sold']} | End: {row['after']}")
    else:
        print("  (No data)")

print("\nSuccess! Saved to dataset/orders.csv and dataset/order_items.csv")
