import pandas as pd
import numpy as np
import time
import os

start = time.time()
print("Loading massive data into Pandas for fast in-memory aggregation...")
orders = pd.read_csv('dataset/orders.csv', usecols=['order_id', 'store_id', 'order_timestamp', 'order_status'])
items = pd.read_csv('dataset/order_items.csv', usecols=['order_id', 'sku_id', 'quantity'])
stores = pd.read_csv('dataset/dark_stores.csv', usecols=['store_id', 'zone', 'capacity_units'])
products = pd.read_csv('dataset/products.csv', usecols=['sku_id', 'category', 'unit_cost', 'mrp'])

# 1. Daily Sales Aggregation
print("Aggregating sales...")
orders = orders[orders['order_status'] == 'delivered']
oi = items.merge(orders, on='order_id')
oi['snapshot_date'] = pd.to_datetime(oi['order_timestamp']).dt.date

sales = oi.groupby(['store_id', 'sku_id', 'snapshot_date'])['quantity'].sum().reset_index()
sales.rename(columns={'quantity': 'sold_qty'}, inplace=True)
sales['snapshot_date'] = pd.to_datetime(sales['snapshot_date'])

# 2. Base Grid
print("Building continuous date grid...")
dates = pd.date_range(start='2025-01-01', end='2025-03-31', freq='D')
grid = pd.MultiIndex.from_product([stores['store_id'], products['sku_id'], dates], names=['store_id', 'sku_id', 'snapshot_date']).to_frame(index=False)

print("Merging grid with sales...")
grid = grid.merge(sales, on=['store_id', 'sku_id', 'snapshot_date'], how='left')
grid['sold_qty'] = grid['sold_qty'].fillna(0)

# 3. Features
print("Calculating lag and rolling features...")
grid = grid.sort_values(['store_id', 'sku_id', 'snapshot_date'])

# MySQL DAYOFWEEK logic (1=Sun, 7=Sat) to match the previous behavior
grid['day_of_week'] = (grid['snapshot_date'].dt.dayofweek + 2) % 7
grid['day_of_week'] = grid['day_of_week'].replace(0, 7)
grid['is_weekend'] = grid['day_of_week'].isin([1, 7]).astype(int)
grid['day_of_month'] = grid['snapshot_date'].dt.day

# Lags
grid['sales_lag_1'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(1)
grid['sales_lag_7'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(7)
grid['sales_lag_28'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(28)

# Rolling
grid['rolling_7day_avg'] = grid.groupby(['store_id', 'sku_id'])['sales_lag_1'].transform(lambda x: x.rolling(7, min_periods=1).mean())
grid['rolling_7day_stddev'] = grid.groupby(['store_id', 'sku_id'])['sales_lag_1'].transform(lambda x: x.rolling(7, min_periods=1).std())

print("Joining static features...")
grid = grid.merge(products, on='sku_id')
grid = grid.merge(stores, on='store_id')

grid['target_sold_qty'] = grid['sold_qty']

# 4. Clean
print("Dropping rows without full 28-day history...")
clean = grid.dropna(subset=['sales_lag_28', 'rolling_7day_avg']).copy()

# Ensure matching column order (or at least all needed columns exist)
feature_cols = [
    'store_id', 'sku_id', 'snapshot_date', 'day_of_week', 'is_weekend', 
    'day_of_month', 'sales_lag_1', 'sales_lag_7', 'sales_lag_28', 
    'rolling_7day_avg', 'rolling_7day_stddev', 'category', 
    'zone', 'capacity_units', 'unit_cost', 'mrp', 'target_sold_qty'
]
clean = clean[feature_cols]

print(f"Saving final CSV with {len(clean)} rows...")
clean.to_csv('forecasting/forecasting_features_final.csv', index=False)

print(f"Pandas processing completely finished in {time.time() - start:.2f} seconds!")
