import os
import time
import subprocess
import pandas as pd

start_time = time.time()
print("Exporting features directly using MySQL CLI (blazing fast)...")

# Use cmd.exe to redirect output cleanly (avoids PowerShell UTF-16 BOM issues)
cmd = 'cmd.exe /c "mysql -u root -pmysql@2027 zepto_inventory -e \\"SELECT * FROM view_forecast_features_clean;\\" > forecasting/forecasting_features_v2.tsv"'
subprocess.run(cmd, shell=True)

print(f"MySQL export finished in {time.time() - start_time:.2f} seconds!")

print(f"Total export complete in {time.time() - start_time:.2f} seconds!")
