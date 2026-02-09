# Install/Update Dependencies Script
# Run this to install or update all required Python packages

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10 or higher." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installing Backend Dependencies..." -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow

try {
    Set-Location backend
    
    Write-Host ""
    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    
    Write-Host ""
    Write-Host "Installing requirements..." -ForegroundColor Cyan
    pip install -r requirements.txt
    
    Write-Host ""
    Write-Host "✓ Backend dependencies installed successfully!" -ForegroundColor Green
    
    Set-Location ..
} catch {
    Write-Host "✗ Failed to install backend dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host ""
Write-Host "Installing Frontend Dependencies..." -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

try {
    Set-Location frontend
    
    Write-Host ""
    Write-Host "Installing requirements..." -ForegroundColor Cyan
    pip install -r requirements.txt
    
    Write-Host ""
    Write-Host "✓ Frontend dependencies installed successfully!" -ForegroundColor Green
    
    Set-Location ..
} catch {
    Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ All dependencies installed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Verifying critical packages..." -ForegroundColor Yellow
Write-Host ""

$packages = @(
    "fastapi",
    "uvicorn",
    "streamlit",
    "azure-identity",
    "azure-mgmt-costmanagement",
    "azure-storage-blob",
    "pandas"
)

$allInstalled = $true
foreach ($package in $packages) {
    try {
        $result = pip show $package 2>&1
        if ($LASTEXITCODE -eq 0) {
            $version = ($result | Select-String "Version:").ToString().Split(":")[1].Trim()
            Write-Host "✓ $package ($version)" -ForegroundColor Green
        } else {
            Write-Host "✗ $package - NOT INSTALLED" -ForegroundColor Red
            $allInstalled = $false
        }
    } catch {
        Write-Host "✗ $package - NOT INSTALLED" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""

if ($allInstalled) {
    Write-Host "All critical packages are installed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Configure AWS Security Group (see AWS_SETUP_SUMMARY.md)"
    Write-Host "  2. Run: ./configure_aws.ps1"
    Write-Host "  3. Run: ./configure_firewall.ps1"
    Write-Host "  4. Run: ./run_local.ps1"
} else {
    Write-Host "⚠ Some packages failed to install. Please check the errors above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try running manually:" -ForegroundColor Cyan
    Write-Host "  cd backend"
    Write-Host "  pip install -r requirements.txt"
    Write-Host "  cd ../frontend"
    Write-Host "  pip install -r requirements.txt"
}

Write-Host ""
