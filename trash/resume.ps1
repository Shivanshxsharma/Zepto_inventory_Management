Write-Host "Creating covering indexes for massive speedup..."
$index_sql = "CREATE INDEX idx_orders_cov ON orders(order_status, store_id, order_timestamp, order_id); CREATE INDEX idx_oi_cov ON order_items(order_id, sku_id, quantity, unit_price_at_sale);"
$index_sql | mysql -u root -pmysql@2027 zepto_inventory

$files = @(
    "tables\daily_sales.sql",
    "tables\daily_movement.sql",
    "tables\wastage_log.sql",
    "tables\snapshot.sql"
)

foreach ($file in $files) {
    Write-Host "Running $file"
    Get-Content $file | mysql -u root -pmysql@2027 zepto_inventory
}
Get-ChildItem -Path "kpis\*.sql" | ForEach-Object {
    Write-Host "Running $($_.Name)"
    Get-Content $_.FullName | mysql -u root -pmysql@2027 zepto_inventory
}
