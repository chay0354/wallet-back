# PowerShell script to kill process on port 8000
$port = 8000
Write-Host "Checking for processes on port $port..."

$connections = netstat -ano | findstr ":$port"
if ($connections) {
    $pids = $connections | ForEach-Object {
        if ($_ -match '\s+(\d+)$') {
            $matches[1]
        }
    } | Select-Object -Unique
    
    foreach ($pid in $pids) {
        Write-Host "Killing process $pid on port $port..."
        taskkill /PID $pid /F
    }
    Write-Host "Port $port is now free!" -ForegroundColor Green
} else {
    Write-Host "No process found on port $port" -ForegroundColor Yellow
}


