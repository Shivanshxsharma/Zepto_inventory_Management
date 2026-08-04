import pandas as pd
import numpy as np
import xgboost as xgb
import sqlalchemy
import urllib.parse

print("Loading features...")
df = pd.read_csv('forecasting/new.tsv', sep='\t')
df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])

# Train/Test Split: Train on Jan-Feb, Test on whole month of March
train = df[df['snapshot_date'] < '2025-03-01'].copy()
test = df[df['snapshot_date'] >= '2025-03-01'].copy()

print(f"Test period covers {test['snapshot_date'].min()} to {test['snapshot_date'].max()}")

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

print("Training model to get predictions...")
model = xgb.XGBRegressor(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    enable_categorical=True, tree_method='hist',
    early_stopping_rounds=20, eval_metric='mae',
    objective='reg:tweedie', tweedie_variance_power=1.9
)

model.fit(
    train[model_features], train[target_col],
    eval_set=[(test[model_features], test[target_col])],
    verbose=False
)

print("Generating predictions on test set...")
preds = model.predict(test[model_features])
test['predicted_demand'] = np.clip(preds, 0, None)
print("Assembling final ML predictions output...")

# Only keep the raw ML outputs for SQL
final_cols = [
    'store_id', 'sku_id', 'snapshot_date', 
    'target_sold_qty', 'predicted_demand'
]
final_df = test[final_cols]

out_path = 'forecasting/ml_predictions.csv'
final_df.to_csv(out_path, index=False)
print(f"\nDone! Exported {len(final_df):,} rows to {out_path}.")
print("You can now load this into MySQL as a table to calculate Reorder Points in SQL.")
