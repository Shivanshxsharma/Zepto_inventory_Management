import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error

# 1. Load the cleaned 90-day window dataset
print("Loading data...")
df = pd.read_csv("forecasting/new.tsv", sep='\t')
df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])

# 2. Chronological split
split_date = df['snapshot_date'].quantile(0.68, interpolation='nearest')
train = df[df['snapshot_date'] <= split_date].copy()
test = df[df['snapshot_date'] > split_date].copy()

print(f"Split date: {split_date}")
print(f"Train: {train.shape[0]:,} rows, {train['snapshot_date'].nunique()} days")
print(f"Test:  {test.shape[0]:,} rows, {test['snapshot_date'].nunique()} days")

# 3. Feature prep
categorical_cols = ['category', 'zone']
for col in categorical_cols:
    train[col] = train[col].astype('category')
    test[col] = test[col].astype('category')

feature_cols = [
    'store_id', 'sku_id', 'day_of_week', 'is_weekend', 'day_of_month',
    'sales_lag_1', 'sales_lag_7', 'sales_lag_28',
    'rolling_7day_avg', 'rolling_7day_stddev',
    'category', 'zone', 'capacity_units',
    'unit_cost', 'mrp'
]
target_col = 'target_sold_qty'

X_train, y_train = train[feature_cols], train[target_col]
X_test, y_test = test[feature_cols], test[target_col]

print("Training model...")
# 4. Train
model = xgb.XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    enable_categorical=True,
    tree_method='hist',
    early_stopping_rounds=20,
    eval_metric='mae',
    objective='reg:tweedie',
    tweedie_variance_power=1.5
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=True
)

# 5. Evaluate
print("\nEvaluating model...")
preds = model.predict(X_test)
preds = preds.clip(min=0)

mae = mean_absolute_error(y_test, preds)
nonzero_mask = y_test > 0
mape_nonzero = mean_absolute_percentage_error(y_test[nonzero_mask], preds[nonzero_mask])

print(f"\nMAE: {mae:.3f}")
print(f"MAPE (non-zero actuals only): {mape_nonzero*100:.1f}%")

# Baseline 1: always predict 0
naive_zero_preds = [0] * len(y_test)
naive_zero_mae = mean_absolute_error(y_test, naive_zero_preds)

# Baseline 2: predict last week's same day (lag_7) as this week's value
# handle any NaN in sales_lag_7 by filling with 0 before scoring
naive_lag7_preds = test['sales_lag_7'].fillna(0)
naive_lag7_mae = mean_absolute_error(y_test, naive_lag7_preds)

# Baseline 3: predict the trailing 7-day rolling average
naive_rolling_preds = test['rolling_7day_avg'].fillna(0)
naive_rolling_mae = mean_absolute_error(y_test, naive_rolling_preds)

# Baseline 4: predict yesterday's value (lag_1) -- simplest possible forecast
naive_lag1_preds = test['sales_lag_1'].fillna(0)
naive_lag1_mae = mean_absolute_error(y_test, naive_lag1_preds)

print("\n=== BASELINE COMPARISON ===")
print(f"Naive (always predict 0):     MAE = {naive_zero_mae:.4f}")
print(f"Naive (yesterday's value):    MAE = {naive_lag1_mae:.4f}")
print(f"Naive (same day last week):   MAE = {naive_lag7_mae:.4f}")
print(f"Naive (7-day rolling avg):    MAE = {naive_rolling_mae:.4f}")
print(f"XGBoost model:                MAE = {mae:.4f}")

# Compute % improvement of XGBoost over the BEST naive baseline
best_naive_mae = min(naive_zero_mae, naive_lag1_mae, naive_lag7_mae, naive_rolling_mae)
improvement_pct = (best_naive_mae - mae) / best_naive_mae * 100
print(f"\nBest naive baseline MAE: {best_naive_mae:.4f}")
print(f"XGBoost improvement over best naive baseline: {improvement_pct:.1f}%")

print("\n=== TARGET DISTRIBUTION (test set) ===")
print(y_test.value_counts(normalize=True).head(10))
print(f"\n% of test rows where target_sold_qty == 0: {(y_test == 0).mean() * 100:.1f}%")
