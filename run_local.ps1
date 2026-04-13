# Startup Script for Azure Cost Dashboard

Write-Host "Starting Azure Cost Dashboard..." -ForegroundColor Green

# Set up paths
$rootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"

# Check requirements
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# Check for critical dependencies
$missingDeps = $false
if (-not (Get-Command "uvicorn" -ErrorAction SilentlyContinue)) {
    # Check if module is importable
    python -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Uvicorn not found. Installing backend dependencies..." -ForegroundColor Yellow
        $missingDeps = $true
    }
}
if (-not (Get-Command "streamlit" -ErrorAction SilentlyContinue)) {
    # Check if module is importable
    python -c "import streamlit" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Streamlit not found. Installing frontend dependencies..." -ForegroundColor Yellow
        $missingDeps = $true
    }
}

# Install dependencies if flag provided or if missing critical deps
if ($args[0] -eq "--install" -or $missingDeps) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r backend/requirements.txt
    pip install -r frontend/requirements.txt
}

# Ensure .env exists
if (-not (Test-Path "backend/.env")) {
    Write-Host "Creating backend/.env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" "backend/.env"
}
if (-not (Test-Path "frontend/.env")) {
    Write-Host "Creating frontend/.env..." -ForegroundColor Yellow
    Set-Content "frontend/.env" "BACKEND_URL=http://localhost:8080"
}

# Start Backend
Write-Host "Starting Backend (Port 8080)..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload" -WorkingDirectory $backendPath -NoNewWindow

# Wait for backend
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "Starting Frontend (Port 8502)..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "-m streamlit run app.py --server.port 8502" -WorkingDirectory $frontendPath -NoNewWindow

Write-Host "Services started! Press Ctrl+C to stop." -ForegroundColor Green
