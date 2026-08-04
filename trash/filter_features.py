import pandas as pd
import time

start = time.time()
print("Loading CSV...")
cols = [
    'store_id', 'sku_id', 'snapshot_date', 'day_of_week', 'is_weekend', 
    'day_of_month', 'sales_lag_1', 'sales_lag_7', 'sales_lag_28', 
    'rolling_7day_avg', 'rolling_7day_stddev', 'category', 'sku_demand_weight', 
    'zone', 'capacity_units', 'unit_cost', 'mrp', 'target_sold_qty'
]
df = pd.read_csv('forecasting/forecasting_features_v2.tsv', sep='\t', low_memory=False)

print("Fixing date column and dropping the ghost column...")
df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
df = df.drop(columns=['sku_demand_weight'], errors='ignore')

print("Filtering to remove April dates...")
df = df[df['snapshot_date'] <= '2025-03-31']

print("Saving final CSV...")
df.to_csv('forecasting/forecasting_features_final.csv', index=False)
print(f"Done in {time.time() - start:.2f} seconds!")
