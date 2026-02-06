# Startup Script for Azure Cost Dashboard

Write-Host "Starting Azure Cost Dashboard..." -ForegroundColor Green

# Check requirements
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# Install dependencies if flag provided
if ($args[0] -eq "--install") {
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
    Set-Content "frontend/.env" "BACKEND_URL=http://localhost:8000"
}

# Start Backend
Write-Host "Starting Backend (Port 8000)..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory "$PSScriptRoot\backend" -NoNewWindow

# Wait for backend
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "Starting Frontend (Port 8501)..." -ForegroundColor Cyan
Start-Process -FilePath "streamlit" -ArgumentList "run app.py --server.port 8501" -WorkingDirectory "$PSScriptRoot\frontend" -NoNewWindow

Write-Host "Services started! Press Ctrl+C to stop." -ForegroundColor Green
