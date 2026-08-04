python generate/04_purchase_orders.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python generate/05_orders.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python generate/06_assign_batch_id.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python add_order_date.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

.\rebuild.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-Content kpis\network_summary.sql | mysql -u root -pmysql@2027 --local-infile=1 zepto_inventory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

mysql -u root -pmysql@2027 zepto_inventory -e "SELECT * FROM view_network_summary"
