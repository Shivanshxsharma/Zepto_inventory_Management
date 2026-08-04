import pandas as pd
import time

print("Loading orders.csv...")
start = time.time()
orders = pd.read_csv('dataset/orders.csv')

print("Adding order_date column...")
orders['order_date'] = pd.to_datetime(orders['order_timestamp']).dt.date

print("Saving orders.csv...")
orders.to_csv('dataset/orders.csv', index=False)

print(f"Done in {time.time() - start:.2f} seconds.")
