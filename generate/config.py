"""
config.py -- shared constants for the Zepto Delhi inventory data-generation pipeline.
All generation scripts import from here so the knobs live in one place.
"""

import os
import pandas as pd

# -- Geography --------------------------------------------------------
CITY = "Delhi"

ZONES = ["North Delhi", "South Delhi", "East Delhi", "West Delhi"]

ZONE_STORE_DISTRIBUTION = {
    "South Delhi": 3,
    "North Delhi": 3,
    "West Delhi":  2,
    "East Delhi":  2,
}

ZONE_COORDINATES = {
    "North Delhi": {"lat_range": (28.68, 28.75), "lng_range": (77.15, 77.23)},
    "South Delhi": {"lat_range": (28.50, 28.58), "lng_range": (77.18, 77.25)},
    "East Delhi":  {"lat_range": (28.60, 28.68), "lng_range": (77.27, 77.32)},
    "West Delhi":  {"lat_range": (28.60, 28.68), "lng_range": (77.05, 77.12)},
}

LOCALITY_MAP = {
    "North Delhi": ["Rohini", "Model Town", "Civil Lines", "Ashok Vihar", "Pitampura"],
    "South Delhi": ["Hauz Khas", "Saket", "Greater Kailash", "Vasant Kunj", "Malviya Nagar"],
    "East Delhi":  ["Laxmi Nagar", "Preet Vihar", "Mayur Vihar", "Vivek Vihar"],
    "West Delhi":  ["Rajouri Garden", "Janakpuri", "Dwarka", "Paschim Vihar", "Tilak Nagar"],
}

# -- Entity counts ----------------------------------------------------
NUM_STORES    = 10
NUM_SUPPLIERS = 18
NUM_CUSTOMERS = 50000

# -- Date range: exactly one calendar month + day 0 ----------------------------
DATE_RANGE = ("2024-12-31", "2025-01-31")

# -- Category -> (is_perishable, shelf_life_min_days, shelf_life_max_days) --
CATEGORY_SHELF_LIFE = {
    "Fruits & Vegetables":   (True,    2,    7),
    "Dairy, Bread & Batter": (True,    2,    7),
    "Meats, Fish & Eggs":    (True,    1,    3),
    "Beverages":             (True,   30,  180),
    "Ice Cream & Desserts":  (True,   60,  180),
    "Packaged Food":         (False,  90,  270),
    "Biscuits":              (False,  90,  270),
    "Munchies":              (False,  90,  180),
    "Chocolates & Candies":  (False, 120,  365),
    "Cooking Essentials":    (False, 180,  365),
    "Paan Corner":           (True,    3,   10),
    "Personal Care":         (False, 365,  730),
    "Home & Cleaning":       (False, 365,  730),
    "Health & Hygiene":      (False, 180,  730),
}

# -- Category -> relative demand weight (drives order-item sampling) ----
CATEGORY_DEMAND_WEIGHT = {
    "Fruits & Vegetables":   10,
    "Dairy, Bread & Batter":  9,
    "Beverages":              7,
    "Munchies":               6,
    "Biscuits":               5,
    "Packaged Food":          5,
    "Ice Cream & Desserts":   4,
    "Paan Corner":            4,
    "Chocolates & Candies":   4,
    "Health & Hygiene":       3,
    "Cooking Essentials":     3,
    "Meats, Fish & Eggs":     3,
    "Personal Care":          2,
    "Home & Cleaning":        2,
}

# -- Store-level demand bias (zone affluence + capacity rank) ----------
ZONE_DEMAND_TIER = {
    "South Delhi": 1.3,
    "North Delhi": 1.0,
    "East Delhi":  1.0,
    "West Delhi":  0.9,
}

def get_store_demand_weights(dataset_dir):
    """Return {store_id: demand_weight} using a 60/40 blend of zone tier and capacity rank."""
    stores = pd.read_csv(os.path.join(dataset_dir, "dark_stores.csv"), encoding="utf-8-sig")
    stores_sorted = stores.sort_values("capacity_units", ascending=False).reset_index(drop=True)
    n = len(stores_sorted)
    top_cutoff, mid_cutoff = n // 3, 2 * n // 3
    cap_mult = {}
    for i, row in stores_sorted.iterrows():
        sid = row["store_id"]
        cap_mult[sid] = 1.3 if i < top_cutoff else (1.0 if i < mid_cutoff else 0.8)
    weights = {}
    for _, row in stores.iterrows():
        sid = row["store_id"]
        zone_mult = ZONE_DEMAND_TIER.get(row["zone"], 1.0)
        weights[sid] = round(0.6 * zone_mult + 0.4 * cap_mult[sid], 2)
    return weights

# -- Paths -------------------------------------------------------------
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.join(_SCRIPT_DIR, "..", "dataset")
RAW_CSV_PATH = os.path.join(DATASET_DIR, "zepto_v2.csv")

