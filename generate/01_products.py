"""
01_products.py -- Build the products dimension table from raw zepto_v2.csv.

Reads the raw scrape, deduplicates, assigns sequential sku_id, computes unit_cost,
shelf_life_days, is_perishable, and demand_weight from config.py category mappings.

Output: dataset/products.csv
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    RAW_CSV_PATH,
    DATASET_DIR,
    CATEGORY_SHELF_LIFE,
    CATEGORY_DEMAND_WEIGHT,
)

np.random.seed(42)

# -- 1. Read raw CSV --------------------------------------------------
print("Reading raw CSV ...")
df = pd.read_csv(RAW_CSV_PATH, encoding="latin1")
print(f"  Raw rows: {len(df)}")

# -- 2. Keep only needed columns & rename -----------------------------
df = df[["Category", "name", "mrp", "weightInGms"]].copy()
df.rename(columns={
    "Category":    "category",
    "name":        "sku_name",
    "mrp":         "mrp",
    "weightInGms": "unit_weight_grams",
}, inplace=True)

# Strip whitespace
df["sku_name"] = df["sku_name"].str.strip()
df["category"] = df["category"].str.strip()

# -- 3. Deduplicate on (category, sku_name, mrp, unit_weight_grams) ---
before = len(df)
df.drop_duplicates(
    subset=["category", "sku_name", "mrp", "unit_weight_grams"],
    keep="first",
    inplace=True,
)
df.reset_index(drop=True, inplace=True)
print(f"  After dedup: {len(df)}  (dropped {before - len(df)} exact duplicates)")

# -- 4. Assign sequential sku_id -------------------------------------
df.insert(0, "sku_id", range(1, len(df) + 1))

# -- 5. Compute unit_cost = mrp * U(0.55, 0.75) ----------------------
df["unit_cost"] = (
    df["mrp"] * np.random.uniform(0.55, 0.75, size=len(df))
).round(2)

# -- 6. Map category metadata from config ----------------------------
def _shelf_life(cat):
    info = CATEGORY_SHELF_LIFE.get(cat)
    if info is None:
        return (False, 180)
    is_perish, sl_min, sl_max = info
    return (is_perish, np.random.randint(sl_min, sl_max + 1))

shelf = df["category"].apply(_shelf_life)
df["is_perishable"]   = shelf.apply(lambda x: x[0])
df["shelf_life_days"] = shelf.apply(lambda x: x[1])

df["demand_weight"] = (
    df["category"].map(CATEGORY_DEMAND_WEIGHT).fillna(1).astype(int)
)

# -- 7. Save ----------------------------------------------------------
out_path = os.path.join(DATASET_DIR, "products.csv")
cols = [
    "sku_id", "sku_name", "category", "mrp", "unit_cost",
    "unit_weight_grams", "is_perishable", "shelf_life_days", "demand_weight",
]
df[cols].to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"\nSaved {len(df)} rows -> {out_path}")

# -- 8. Summary stats -------------------------------------------------
print("\n-- Category value counts ---------------------------")
print(df["category"].value_counts().to_string())

print("\n-- Sample rows -------------------------------------")
print(df[cols].sample(10, random_state=42).to_string(index=False))
