import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
import time

# ============================================================
# STAGE 1: Build forecast features in Pandas (fast in-memory)
# ============================================================
start = time.time()
print("=" * 60)
print("STAGE 1: Building forecast features in Pandas")
print("=" * 60)

print("Loading CSVs...")
orders = pd.read_csv('dataset/orders.csv', usecols=['order_id', 'store_id', 'order_timestamp', 'order_status'])
items = pd.read_csv('dataset/order_items.csv', usecols=['order_id', 'sku_id', 'quantity'])
stores = pd.read_csv('dataset/dark_stores.csv', usecols=['store_id', 'zone', 'capacity_units'])
products = pd.read_csv('dataset/products.csv', usecols=['sku_id', 'category', 'unit_cost', 'mrp'])

# 1. Daily Sales Aggregation
print("Aggregating daily sales...")
orders = orders[orders['order_status'] == 'delivered']
oi = items.merge(orders, on='order_id')
oi['snapshot_date'] = pd.to_datetime(oi['order_timestamp']).dt.date

sales = oi.groupby(['store_id', 'sku_id', 'snapshot_date'])['quantity'].sum().reset_index()
sales.rename(columns={'quantity': 'sold_qty'}, inplace=True)
sales['snapshot_date'] = pd.to_datetime(sales['snapshot_date'])

# 2. Base Grid (continuous date grid -- no gaps)
print("Building continuous date grid (store x sku x date)...")
dates = pd.date_range(start='2025-01-01', end='2025-03-31', freq='D')
grid = pd.MultiIndex.from_product(
    [stores['store_id'], products['sku_id'], dates],
    names=['store_id', 'sku_id', 'snapshot_date']
).to_frame(index=False)

print("Merging grid with sales (LEFT JOIN, fill zeros)...")
grid = grid.merge(sales, on=['store_id', 'sku_id', 'snapshot_date'], how='left')
grid['sold_qty'] = grid['sold_qty'].fillna(0)

# 3. Calendar Features
print("Calculating calendar, lag, and rolling features...")
grid = grid.sort_values(['store_id', 'sku_id', 'snapshot_date'])

# MySQL DAYOFWEEK logic (1=Sun, 7=Sat)
grid['day_of_week'] = (grid['snapshot_date'].dt.dayofweek + 2) % 7
grid['day_of_week'] = grid['day_of_week'].replace(0, 7)
grid['is_weekend'] = grid['day_of_week'].isin([1, 7]).astype(int)
grid['day_of_month'] = grid['snapshot_date'].dt.day

# 4. Lag Features
grid['sales_lag_1'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(1)
grid['sales_lag_7'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(7)
grid['sales_lag_28'] = grid.groupby(['store_id', 'sku_id'])['sold_qty'].shift(28)

# 5. Rolling Features (trailing 7 days, excluding current day)
grid['rolling_7day_avg'] = grid.groupby(['store_id', 'sku_id'])['sales_lag_1'].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)
grid['rolling_7day_stddev'] = grid.groupby(['store_id', 'sku_id'])['sales_lag_1'].transform(
    lambda x: x.rolling(7, min_periods=1).std()
)

# 6. Join Static Features
print("Joining static features (products, stores)...")
grid = grid.merge(products, on='sku_id')
grid = grid.merge(stores, on='store_id')

grid['target_sold_qty'] = grid['sold_qty']

# 7. Clean -- drop rows without full 28-day history
print("Dropping rows without full 28-day lag history...")
clean = grid.dropna(subset=['sales_lag_28', 'rolling_7day_avg']).copy()

feature_cols = [
    'store_id', 'sku_id', 'snapshot_date', 'day_of_week', 'is_weekend',
    'day_of_month', 'sales_lag_1', 'sales_lag_7', 'sales_lag_28',
    'rolling_7day_avg', 'rolling_7day_stddev', 'category',
    'zone', 'capacity_units', 'unit_cost', 'mrp', 'target_sold_qty'
]
clean = clean[feature_cols]

# 8. Save as TSV (new.tsv) and CSV
print(f"Saving {len(clean):,} rows to forecasting/new.tsv ...")
clean.to_csv('forecasting/new.tsv', sep='\t', index=False)
print(f"Saving {len(clean):,} rows to forecasting/forecasting_features_final.csv ...")
clean.to_csv('forecasting/forecasting_features_final.csv', index=False)

stage1_time = time.time() - start
print(f"\nSTAGE 1 complete in {stage1_time:.1f} seconds. ({len(clean):,} rows)")

# ============================================================
# STAGE 2: Train XGBoost
# ============================================================
print("\n" + "=" * 60)
print("STAGE 2: Training XGBoost model")
print("=" * 60)

df = clean.copy()
df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])

# Chronological split
split_date = df['snapshot_date'].quantile(0.68, interpolation='nearest')
train = df[df['snapshot_date'] <= split_date].copy()
test = df[df['snapshot_date'] > split_date].copy()

print(f"Split date: {split_date.date()}")
print(f"Train: {train.shape[0]:,} rows, {train['snapshot_date'].nunique()} days")
print(f"Test:  {test.shape[0]:,} rows, {test['snapshot_date'].nunique()} days")

# Feature prep
categorical_cols = ['category', 'zone']
for col in categorical_cols:
    train[col] = train[col].astype('category')
    test[col] = test[col].astype('category')

model_features = [
    'store_id', 'sku_id', 'day_of_week', 'is_weekend', 'day_of_month',
    'sales_lag_1', 'sales_lag_7', 'sales_lag_28',
    'rolling_7day_avg', 'rolling_7day_stddev',
    'category', 'zone', 'capacity_units',
    'unit_cost', 'mrp'
]
target_col = 'target_sold_qty'

X_train, y_train = train[model_features], train[target_col]
X_test, y_test = test[model_features], test[target_col]

print("Training XGBoost (Tweedie, 300 rounds, early stopping)...")
model = xgb.XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    enable_categorical=True,
    tree_method='hist',
    early_stopping_rounds=20,
    eval_metric='mae',
    objective='reg:tweedie',
    tweedie_variance_power=1.9
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=True
)

# Evaluate
print("\n" + "=" * 60)
print("STAGE 3: Evaluation")
print("=" * 60)

preds = model.predict(X_test)
preds = preds.clip(min=0)

mae = mean_absolute_error(y_test, preds)
nonzero_mask = y_test > 0
mape_nonzero = mean_absolute_percentage_error(y_test[nonzero_mask], preds[nonzero_mask])

print(f"\nMAE: {mae:.3f}")
print(f"MAPE (non-zero actuals only): {mape_nonzero*100:.1f}%")

# Baselines
naive_zero_mae = mean_absolute_error(y_test, [0] * len(y_test))
naive_lag1_mae = mean_absolute_error(y_test, test['sales_lag_1'].fillna(0))
naive_lag7_mae = mean_absolute_error(y_test, test['sales_lag_7'].fillna(0))
naive_rolling_mae = mean_absolute_error(y_test, test['rolling_7day_avg'].fillna(0))

print("\n=== BASELINE COMPARISON ===")
print(f"Naive (always predict 0):     MAE = {naive_zero_mae:.4f}")
print(f"Naive (yesterday's value):    MAE = {naive_lag1_mae:.4f}")
print(f"Naive (same day last week):   MAE = {naive_lag7_mae:.4f}")
print(f"Naive (7-day rolling avg):    MAE = {naive_rolling_mae:.4f}")
print(f"XGBoost model:                MAE = {mae:.4f}")

best_naive_mae = min(naive_zero_mae, naive_lag1_mae, naive_lag7_mae, naive_rolling_mae)
improvement_pct = (best_naive_mae - mae) / best_naive_mae * 100
print(f"\nBest naive baseline MAE: {best_naive_mae:.4f}")
print(f"XGBoost improvement over best naive baseline: {improvement_pct:.1f}%")

print("\n=== TARGET DISTRIBUTION (test set) ===")
print(y_test.value_counts(normalize=True).head(10))
print(f"\n% of test rows where target_sold_qty == 0: {(y_test == 0).mean() * 100:.1f}%")

total_time = time.time() - start
print(f"\n{'=' * 60}")
print(f"TOTAL PIPELINE TIME: {total_time:.1f} seconds")
print(f"{'=' * 60}")
