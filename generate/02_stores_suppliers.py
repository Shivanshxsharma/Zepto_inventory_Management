"""
02_stores_suppliers.py -- Generate dark_stores, suppliers, and product_suppliers tables.

Uses Faker for supplier names, and numpy for coordinate and random value generation.
Stores are distributed across Delhi zones per config.py.
"""

import os
import sys
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    DATASET_DIR, DATE_RANGE, NUM_STORES, NUM_SUPPLIERS, CITY,
    ZONES, ZONE_STORE_DISTRIBUTION, ZONE_COORDINATES, LOCALITY_MAP
)

np.random.seed(42)
fake = Faker('en_IN')
Faker.seed(42)

start_date = datetime.strptime(DATE_RANGE[0], "%Y-%m-%d")

# -- 1. DARK STORES ---------------------------------------------------
stores = []
store_id = 1

for zone in ZONES:
    num_zone_stores = ZONE_STORE_DISTRIBUTION.get(zone, 0)
    for _ in range(num_zone_stores):
        locality = np.random.choice(LOCALITY_MAP[zone])
        lat_min, lat_max = ZONE_COORDINATES[zone]["lat_range"]
        lng_min, lng_max = ZONE_COORDINATES[zone]["lng_range"]
        
        lat = np.random.uniform(lat_min, lat_max)
        lng = np.random.uniform(lng_min, lng_max)
        
        opened_days_ago = np.random.randint(365, 365 * 3 + 1)
        opened_date = start_date - timedelta(days=opened_days_ago)
        
        stores.append({
            "store_id": store_id,
            "store_name": f"Zepto - {locality}",
            "city": CITY,
            "zone": zone,
            "locality": locality,
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "capacity_units": np.random.randint(2000, 5000 + 1),
            "opened_date": opened_date.strftime("%Y-%m-%d"),
        })
        store_id += 1

stores_df = pd.DataFrame(stores)
stores_path = os.path.join(DATASET_DIR, "dark_stores.csv")
stores_df.to_csv(stores_path, index=False, encoding="utf-8-sig")
print(f"Saved {len(stores_df)} dark stores -> {stores_path}")

# -- 2. SUPPLIERS -----------------------------------------------------
suppliers = []
for i in range(1, NUM_SUPPLIERS + 1):
    suppliers.append({
        "supplier_id": i,
        "supplier_name": fake.company(),
        "city": CITY,
        "avg_lead_time_days": np.random.randint(2, 7 + 1),
    })

suppliers_df = pd.DataFrame(suppliers)
suppliers_path = os.path.join(DATASET_DIR, "suppliers.csv")
suppliers_df.to_csv(suppliers_path, index=False, encoding="utf-8-sig")
print(f"Saved {len(suppliers_df)} suppliers -> {suppliers_path}")

# -- 3. PRODUCT_SUPPLIERS ---------------------------------------------
products = pd.read_csv(os.path.join(DATASET_DIR, "products.csv"), encoding="utf-8-sig")
supplier_ids = suppliers_df["supplier_id"].values

rows = []
for _, prod in products.iterrows():
    num_suppliers = np.random.choice([1, 2], p=[0.7, 0.3])
    chosen = np.random.choice(supplier_ids, size=num_suppliers, replace=False)
    for sid in chosen:
        # cost_price +/- 5% of unit_cost
        variation = np.random.uniform(0.95, 1.05)
        cost_price = round(prod["unit_cost"] * variation, 2)
        rows.append({
            "sku_id": int(prod["sku_id"]),
            "supplier_id": sid,
            "cost_price": cost_price,
        })

ps_df = pd.DataFrame(rows)
ps_path = os.path.join(DATASET_DIR, "product_suppliers.csv")
ps_df.to_csv(ps_path, index=False, encoding="utf-8-sig")
print(f"Saved {len(ps_df)} product-supplier links -> {ps_path}")
print(f"  SKUs with 1 supplier: {(ps_df.groupby('sku_id').size() == 1).sum()}")
print(f"  SKUs with 2 suppliers: {(ps_df.groupby('sku_id').size() == 2).sum()}")
