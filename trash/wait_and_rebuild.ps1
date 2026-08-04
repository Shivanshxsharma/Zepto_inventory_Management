$locked = $true
Write-Host "Waiting for MySQL Crash Recovery to finish releasing locks..."

while ($locked) {
    # Try to drop database with a 2-second timeout
    $result = cmd /c "echo SET SESSION lock_wait_timeout = 2; DROP DATABASE IF EXISTS zepto_inventory; | mysql -u root -pmysql@2027 2>&1"
    
    if ($result -match "Lock wait timeout exceeded") {
        # Still locked
        Start-Sleep -Seconds 10
    } else {
        $locked = $false
        Write-Host "LOCK RELEASED! CRASH RECOVERY COMPLETE!"
    }
}

Write-Host "Starting full rebuild pipeline..."
powershell -ExecutionPolicy Bypass -File rebuild.ps1
