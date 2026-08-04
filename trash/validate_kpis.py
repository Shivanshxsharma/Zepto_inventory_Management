import os
import pandas as pd

dataset_dir = "d:/Zepto_Delhi_inventory/dataset"

# Load data
print("Loading data...")
po = pd.read_csv(os.path.join(dataset_dir, "purchase_orders.csv"))
oi = pd.read_csv(os.path.join(dataset_dir, "order_items.csv"))
orders = pd.read_csv(os.path.join(dataset_dir, "orders.csv"))

print("\n=== KPI VALIDATION ===")

# 1. Quantities and Ratio
total_purchased = po["quantity_ordered"].sum()
total_sold = oi["quantity"].sum()
ratio = (total_sold / total_purchased) * 100 if total_purchased else 0

print(f"Total Quantity Ordered (Purchased): {total_purchased:,}")
print(f"Total Quantity Sold:                {total_sold:,}")
print(f"Sold / Purchased Ratio:             {ratio:.2f}%  (Target: 60-85%)")

if 60 <= ratio <= 85:
    print("  -> Ratio is within target range!")
else:
    print("  -> WARNING: Ratio is OUTSIDE target range.")

# 2. Orders per customer per month
total_delivered = len(orders[orders["order_status"] == "delivered"])
orders_per_month = (total_delivered / 50000) / 3

print(f"\nTotal Delivered Orders: {total_delivered:,}")
print(f"Total Customers: 50,000")
print(f"Orders per Customer per Month: {orders_per_month:.2f}  (Target: 2-6)")

if 2 <= orders_per_month <= 6:
    print("  -> Orders per customer is within target range!")
else:
    print("  -> WARNING: Orders per customer is OUTSIDE target range.")

# 3. Item Quantity Distribution
print("\nItem Quantity Distribution (order_items['quantity'].value_counts(normalize=True)):")
dist = oi["quantity"].value_counts(normalize=True).sort_index()
for q, pct in dist.items():
    print(f"  Qty {q}: {pct * 100:.2f}%")

# 4. Store Discipline
print("\nStore Discipline Assignment:")
print("  Tight (low-waste) stores: [1, 2, 6, 8, 9]")
print("  Loose (moderate-waste) stores: [3, 4, 5, 7, 10]")

print("\nValidation script finished.")
