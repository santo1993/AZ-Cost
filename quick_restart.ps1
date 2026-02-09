# Quick Restart - Azure Cost Dashboard
# Fast restart without extensive checks

Write-Host "Quick Restart - Azure Cost Dashboard" -ForegroundColor Cyan
Write-Host ""

# Set up paths
$rootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"

# Kill processes on ports 8000 and 8501
Write-Host "Stopping services..." -ForegroundColor Yellow

# Backend (Port 8000)
$backendProcess = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
if ($backendProcess) {
    $backendProcess -match '\s+(\d+)\s*$' | Out-Null
    $pid = $matches[1]
    if ($pid) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Backend stopped" -ForegroundColor Green
    }
}

# Frontend (Port 8501)
$frontendProcess = netstat -ano | Select-String ":8501" | Select-String "LISTENING"
if ($frontendProcess) {
    $frontendProcess -match '\s+(\d+)\s*$' | Out-Null
    $pid = $matches[1]
    if ($pid) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Frontend stopped" -ForegroundColor Green
    }
}

Start-Sleep -Seconds 2

# Start services
Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow

# Start Backend
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory $backendPath -NoNewWindow
Write-Host "  ✓ Backend starting..." -ForegroundColor Green

Start-Sleep -Seconds 3

# Start Frontend
Start-Process -FilePath "python" -ArgumentList "-m streamlit run app.py --server.port 8501" -WorkingDirectory $frontendPath -NoNewWindow
Write-Host "  ✓ Frontend starting..." -ForegroundColor Green

Write-Host ""
Write-Host "Services restarted!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Wait 5-10 seconds for services to fully start..." -ForegroundColor Gray
Write-Host ""
