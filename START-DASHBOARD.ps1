# Quick Start Script for Azure Cost Dashboard
# Uses ports 8080 (backend) and 8502 (frontend)
#
#

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Azure Cost Dashboard - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if services are already running
$backendRunning = netstat -ano | Select-String ":8080 " | Select-String "LISTENING"
$frontendRunning = netstat -ano | Select-String ":8502 " | Select-String "LISTENING"

if ($backendRunning -or $frontendRunning) {
    Write-Host "WARNING: Services are already running!" -ForegroundColor Yellow
    Write-Host ""
    if ($backendRunning) { Write-Host "  + Backend on port 8080" -ForegroundColor Green }
    if ($frontendRunning) { Write-Host "  + Frontend on port 8502" -ForegroundColor Green }
    Write-Host ""
    Write-Host "Access the dashboard at:" -ForegroundColor Cyan
    Write-Host "  http://localhost:8502" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Do you want to restart? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Cancelled." -ForegroundColor Gray
        exit 0
    }
    
    Write-Host ""
    Write-Host "Stopping existing services..." -ForegroundColor Yellow
    & "$PSScriptRoot\manage.ps1" stop
    Start-Sleep -Seconds 2
}

# Check for blocked ports
$port8000Blocked = netstat -ano | Select-String ":8000 " | Select-String "LISTENING" | Select-String " 4$"
$port8501Blocked = netstat -ano | Select-String ":8501 " | Select-String "LISTENING" | Select-String " 4$"

if ($port8000Blocked -or $port8501Blocked) {
    Write-Host "Note: Ports 8000 and 8501 are blocked by Windows" -ForegroundColor Yellow
    Write-Host "Using alternative ports 8080 and 8502 instead" -ForegroundColor Yellow
    Write-Host ""
}

# Start services
Write-Host "Starting Azure Cost Dashboard..." -ForegroundColor Green
Write-Host ""
Write-Host "   Backend:  Port 8080" -ForegroundColor Cyan
Write-Host "   Frontend: Port 8502" -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\manage.ps1" start -Background

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dashboard Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Cyan
Write-Host "  Dashboard:  http://localhost:8502" -ForegroundColor White
Write-Host "  API:        http://localhost:8080" -ForegroundColor White
Write-Host "  API Docs:   http://localhost:8080/docs" -ForegroundColor White
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  Status:  .\manage.ps1 status" -ForegroundColor Gray
Write-Host "  Stop:    .\manage.ps1 stop" -ForegroundColor Gray
Write-Host "  Logs:    .\manage.ps1 logs" -ForegroundColor Gray
Write-Host ""

# Wait a moment and verify
Start-Sleep -Seconds 3

Write-Host "Verifying services..." -ForegroundColor Gray
$backendCheck = netstat -ano | Select-String ":8080 " | Select-String "LISTENING"
$frontendCheck = netstat -ano | Select-String ":8502 " | Select-String "LISTENING"

if ($backendCheck -and $frontendCheck) {
    Write-Host "+ Both services are running!" -ForegroundColor Green
    
    # Try to open browser
    try {
        #Start-Process "http://localhost:8502"
        Write-Host "+ Dashboard opened in browser" -ForegroundColor Green
    } catch {
        Write-Host "! Could not auto-open browser" -ForegroundColor Yellow
        Write-Host "  Please open manually: http://localhost:8502" -ForegroundColor White
    }
} else {
    Write-Host "! Services may still be starting..." -ForegroundColor Yellow
    Write-Host "  Check status with: .\manage.ps1 status" -ForegroundColor White
    Write-Host "  View logs with: .\manage.ps1 logs" -ForegroundColor White
}

Write-Host ""
