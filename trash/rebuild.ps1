$files = @(
    "tables\schema.sql",
    "tables\load_data.sql",
    "tables\add_indexes.sql",
    "tables\daily_sales.sql",
    "tables\daily_movement.sql",
    "tables\wastage_log.sql",
    "tables\snapshot.sql"
)
foreach ($file in $files) {
    Write-Host "Running $file"
    if ($file -eq "tables\schema.sql") {
        Get-Content $file | mysql -u root -pmysql@2027 --local-infile=1
    } else {
        Get-Content $file | mysql -u root -pmysql@2027 --local-infile=1 zepto_inventory
    }
}
Get-ChildItem -Path "kpis\*.sql" | ForEach-Object {
    Write-Host "Running $($_.Name)"
    Get-Content $_.FullName | mysql -u root -pmysql@2027 --local-infile=1 zepto_inventory
}
