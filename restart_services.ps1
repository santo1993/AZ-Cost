# Restart Azure Cost Dashboard Services
# This script stops and restarts both backend and frontend services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Azure Cost Dashboard - Restart Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set up paths
$rootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"

# Function to kill processes by port
function Stop-ProcessByPort {
    param (
        [int]$Port,
        [string]$ServiceName
    )
    
    Write-Host "Stopping $ServiceName (Port $Port)..." -ForegroundColor Yellow
    
    try {
        # Find process using the port
        $processInfo = netstat -ano | Select-String ":$Port" | Select-String "LISTENING"
        
        if ($processInfo) {
            # Extract PID from netstat output
            $processInfo -match '\s+(\d+)\s*$' | Out-Null
            $pid = $matches[1]
            
            if ($pid) {
                Write-Host "  Found process PID: $pid" -ForegroundColor Gray
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
                Write-Host "  ✓ $ServiceName stopped" -ForegroundColor Green
            }
        } else {
            Write-Host "  ℹ $ServiceName not running" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠ Could not stop $ServiceName : $_" -ForegroundColor Yellow
    }
}

# Function to kill Python processes by name
function Stop-PythonProcesses {
    Write-Host "Stopping any remaining Python processes..." -ForegroundColor Yellow
    
    try {
        # Stop uvicorn processes
        Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*streamlit*"
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Start-Sleep -Seconds 1
        Write-Host "  ✓ Python processes cleaned up" -ForegroundColor Green
    } catch {
        Write-Host "  ℹ No Python processes to clean up" -ForegroundColor Gray
    }
}

# Step 1: Stop services
Write-Host ""
Write-Host "Step 1: Stopping Services" -ForegroundColor Cyan
Write-Host "-------------------------" -ForegroundColor Cyan

Stop-ProcessByPort -Port 8000 -ServiceName "Backend"
Stop-ProcessByPort -Port 8501 -ServiceName "Frontend"
Stop-PythonProcesses

Write-Host ""
Write-Host "✓ All services stopped" -ForegroundColor Green
Start-Sleep -Seconds 2

# Step 2: Check Python installation
Write-Host ""
Write-Host "Step 2: Checking Requirements" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan

if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

$pythonVersion = python --version
Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green

# Step 3: Check dependencies
Write-Host ""
Write-Host "Step 3: Checking Dependencies" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan

$missingDeps = $false

# Check uvicorn
python -c "import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Uvicorn not found" -ForegroundColor Red
    $missingDeps = $true
} else {
    Write-Host "  ✓ Uvicorn installed" -ForegroundColor Green
}

# Check streamlit
python -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Streamlit not found" -ForegroundColor Red
    $missingDeps = $true
} else {
    Write-Host "  ✓ Streamlit installed" -ForegroundColor Green
}

# Install dependencies if missing
if ($missingDeps) {
    Write-Host ""
    Write-Host "Installing missing dependencies..." -ForegroundColor Yellow
    pip install -r backend/requirements.txt
    pip install -r frontend/requirements.txt
}

# Step 4: Check configuration files
Write-Host ""
Write-Host "Step 4: Checking Configuration" -ForegroundColor Cyan
Write-Host "------------------------------" -ForegroundColor Cyan

if (-not (Test-Path "backend/.env")) {
    Write-Host "  ⚠ backend/.env not found - using defaults" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ backend/.env found" -ForegroundColor Green
}

if (-not (Test-Path "frontend/.env")) {
    Write-Host "  ⚠ frontend/.env not found - using defaults" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ frontend/.env found" -ForegroundColor Green
}

# Step 5: Start services
Write-Host ""
Write-Host "Step 5: Starting Services" -ForegroundColor Cyan
Write-Host "-------------------------" -ForegroundColor Cyan

# Start Backend
Write-Host "  Starting Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory $backendPath -NoNewWindow
Start-Sleep -Seconds 3

# Check if backend started
$backendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $backendRunning = $true
        Write-Host "  ✓ Backend started successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Backend starting... (may take a moment)" -ForegroundColor Yellow
}

# Start Frontend
Write-Host "  Starting Frontend (Port 8501)..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m streamlit run app.py --server.port 8501" -WorkingDirectory $frontendPath -NoNewWindow
Start-Sleep -Seconds 3

# Check if frontend started
$frontendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $frontendRunning = $true
        Write-Host "  ✓ Frontend started successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Frontend starting... (may take a moment)" -ForegroundColor Yellow
}

# Step 6: Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Restart Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($backendRunning) {
    Write-Host "✓ Backend:  http://localhost:8000" -ForegroundColor Green
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Gray
} else {
    Write-Host "⚠ Backend:  Starting... (check http://localhost:8000 in a moment)" -ForegroundColor Yellow
}

if ($frontendRunning) {
    Write-Host "✓ Frontend: http://localhost:8501" -ForegroundColor Green
} else {
    Write-Host "⚠ Frontend: Starting... (check http://localhost:8501 in a moment)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press Ctrl+C to stop services" -ForegroundColor Gray
Write-Host ""

# Optional: Open browser
$openBrowser = Read-Host "Open dashboard in browser? (Y/N)"
if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "http://localhost:8501"
}

Write-Host ""
Write-Host "Services are running. Keep this window open." -ForegroundColor Cyan
Write-Host "To stop services, run: .\stop_services.ps1" -ForegroundColor Gray
Write-Host ""
