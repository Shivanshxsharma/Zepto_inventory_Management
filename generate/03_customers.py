"""
03_customers.py -- Generate 3,000 synthetic customers for Delhi.

Uses Faker for names and contact info, and NumPy for weighted signup dates.
Assigns each customer to a valid zone and locality based on config maps.
"""

import os
import sys
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    DATASET_DIR, DATE_RANGE, NUM_CUSTOMERS, ZONES, LOCALITY_MAP
)

np.random.seed(42)
fake = Faker('en_IN')
Faker.seed(42)

start_date = datetime.strptime(DATE_RANGE[0], "%Y-%m-%d")

customers = []

for i in range(1, NUM_CUSTOMERS + 1):
    zone = np.random.choice(ZONES)
    locality = np.random.choice(LOCALITY_MAP[zone])
    
    # Signup date: exponentially weighted toward recent dates
    # days_ago ranges 0-730 (2 years).
    # Exponential distribution lambda = 1/180
    days_ago = min(730, int(np.random.exponential(180)))
    signup = start_date - timedelta(days=days_ago)

    customers.append({
        "customer_id": i,
        "customer_name": fake.name(),
        "customer_email": fake.email(),
        "customer_phone": fake.phone_number(),
        "zone": zone,
        "locality": locality,
        "signup_date": signup.strftime("%Y-%m-%d"),
    })

customers_df = pd.DataFrame(customers)
out_path = os.path.join(DATASET_DIR, "customers.csv")
customers_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"Saved {len(customers_df)} customers -> {out_path}")

print("\nSample rows:")
print(customers_df.sample(5, random_state=42).to_string(index=False))
