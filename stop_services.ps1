# Stop Azure Cost Dashboard Services
# This script stops both backend and frontend services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Azure Cost Dashboard - Stop Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

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
                Start-Sleep -Seconds 1
                
                # Verify it stopped
                $stillRunning = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if (-not $stillRunning) {
                    Write-Host "  ✓ $ServiceName stopped successfully" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ $ServiceName may still be running" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "  ℹ $ServiceName not running" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠ Error stopping $ServiceName : $_" -ForegroundColor Yellow
    }
}

# Function to kill all Python processes related to the dashboard
function Stop-DashboardProcesses {
    Write-Host "Stopping all dashboard-related processes..." -ForegroundColor Yellow
    
    try {
        # Get all Python processes
        $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        
        $stoppedCount = 0
        foreach ($proc in $pythonProcesses) {
            try {
                $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                
                # Check if it's uvicorn or streamlit
                if ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*streamlit*") {
                    Write-Host "  Stopping PID $($proc.Id): $($cmdLine.Substring(0, [Math]::Min(60, $cmdLine.Length)))..." -ForegroundColor Gray
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                    $stoppedCount++
                }
            } catch {
                # Ignore errors for individual processes
            }
        }
        
        if ($stoppedCount -gt 0) {
            Write-Host "  ✓ Stopped $stoppedCount dashboard process(es)" -ForegroundColor Green
        } else {
            Write-Host "  ℹ No dashboard processes found" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ℹ No Python processes to clean up" -ForegroundColor Gray
    }
}

# Stop services
Write-Host "Stopping Services..." -ForegroundColor Cyan
Write-Host ""

Stop-ProcessByPort -Port 8000 -ServiceName "Backend (FastAPI)"
Stop-ProcessByPort -Port 8501 -ServiceName "Frontend (Streamlit)"

Write-Host ""
Stop-DashboardProcesses

# Verify services are stopped
Write-Host ""
Write-Host "Verifying services are stopped..." -ForegroundColor Cyan

Start-Sleep -Seconds 2

$backendStopped = $true
$frontendStopped = $true

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $backendStopped = $false
    }
} catch {
    # Expected - service should be stopped
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $frontendStopped = $false
    }
} catch {
    # Expected - service should be stopped
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($backendStopped) {
    Write-Host "✓ Backend (Port 8000):  Stopped" -ForegroundColor Green
} else {
    Write-Host "✗ Backend (Port 8000):  Still running" -ForegroundColor Red
    Write-Host "  Try running this script again or manually kill the process" -ForegroundColor Yellow
}

if ($frontendStopped) {
    Write-Host "✓ Frontend (Port 8501): Stopped" -ForegroundColor Green
} else {
    Write-Host "✗ Frontend (Port 8501): Still running" -ForegroundColor Red
    Write-Host "  Try running this script again or manually kill the process" -ForegroundColor Yellow
}

Write-Host ""

if ($backendStopped -and $frontendStopped) {
    Write-Host "All services stopped successfully!" -ForegroundColor Green
    Write-Host "To restart, run: .\restart_services.ps1" -ForegroundColor Gray
} else {
    Write-Host "Some services may still be running." -ForegroundColor Yellow
    Write-Host "Check Task Manager for any remaining python.exe processes" -ForegroundColor Gray
}

Write-Host ""
