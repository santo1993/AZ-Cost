# Azure Cost Dashboard - Service Manager
# This keeps the services running permanently

param(
    [switch]$Stop
)

$backendPort = 8000
$frontendPort = 8501

if ($Stop) {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "Services stopped!" -ForegroundColor Green
    exit
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Cost Dashboard - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Kill existing processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Backend on port 8000 (directly, no IIS)
Write-Host "Starting Backend on port $backendPort..." -ForegroundColor Yellow
Start-Process -FilePath "C:\Program Files\Python313\python.exe" `
    -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port $backendPort --log-level info" `
    -WorkingDirectory "C:\Project\AZ-Cost\backend" `
    -RedirectStandardOutput "C:\Project\AZ-Cost\backend\logs\backend.log" `
    -RedirectStandardError "C:\Project\AZ-Cost\backend\logs\backend-error.log" `
    -WindowStyle Hidden

# Start Frontend on port 8501 (directly, no IIS)
Write-Host "Starting Frontend on port $frontendPort..." -ForegroundColor Yellow
Start-Process -FilePath "C:\Program Files\Python313\python.exe" `
    -ArgumentList "-m streamlit run app.py --server.port $frontendPort --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false" `
    -WorkingDirectory "C:\Project\AZ-Cost\frontend" `
    -RedirectStandardOutput "C:\Project\AZ-Cost\frontend\logs\frontend.log" `
    -RedirectStandardError "C:\Project\AZ-Cost\frontend\logs\frontend-error.log" `
    -WindowStyle Hidden

Write-Host "Waiting 20 seconds for initialization..." -ForegroundColor Cyan
Start-Sleep -Seconds 20

# Test services
Write-Host "`nTesting Backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "  SUCCESS! Backend is running on port $backendPort" -ForegroundColor Green
    Write-Host "  Response: $($response.Content)" -ForegroundColor Cyan
}
catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTesting Frontend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$frontendPort" -UseBasicParsing -TimeoutSec 10
    Write-Host "  SUCCESS! Frontend is running on port $frontendPort" -ForegroundColor Green
}
catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Services are running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:$backendPort" -ForegroundColor White
Write-Host "Frontend: http://localhost:$frontendPort" -ForegroundColor White
Write-Host "`nTo stop services, run:" -ForegroundColor Yellow
Write-Host "  .\run_services.ps1 -Stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
