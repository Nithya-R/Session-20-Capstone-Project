param (
    [int]$Port = 8000
)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Starting Civic Lens Backend API Server    " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking for existing instances on port $Port..."
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

if ($connections) {
    Write-Host "Port $Port is currently in use. Terminating existing process..." -ForegroundColor Yellow
    foreach ($conn in $connections) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Existing process terminated." -ForegroundColor Green
    Start-Sleep -Seconds 2
}

Write-Host "Entering server loop. Press Ctrl+C to stop completely." -ForegroundColor Magenta

# Infinite loop to keep the server alive
while ($true) {
    Write-Host "-> Launching Uvicorn..." -ForegroundColor Green
    
    # Run uvicorn (blocking call)
    & ".\venv\Scripts\uvicorn.exe" main:app --host 0.0.0.0 --port $Port --reload
    
    Write-Host "-> Uvicorn process exited or crashed." -ForegroundColor Red
    Write-Host "Restarting in 3 seconds... (Press Ctrl+C to abort)" -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}
