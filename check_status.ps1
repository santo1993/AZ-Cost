# Check Status - Azure Cost Dashboard
# Checks if backend and frontend services are running

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Azure Cost Dashboard - Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if port is in use
function Test-Port {
    param (
        [int]$Port,
        [string]$ServiceName
    )
    
    $processInfo = netstat -ano | Select-String ":$Port" | Select-String "LISTENING"
    
    if ($processInfo) {
        $processInfo -match '\s+(\d+)\s*$' | Out-Null
        $pid = $matches[1]
        
        Write-Host "✓ $ServiceName (Port $Port)" -ForegroundColor Green
        Write-Host "  PID: $pid" -ForegroundColor Gray
        
        # Try to get process details
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  Process: $($process.ProcessName)" -ForegroundColor Gray
                Write-Host "  Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
            }
        } catch {
            # Ignore errors
        }
        
        return $true
    } else {
        Write-Host "✗ $ServiceName (Port $Port)" -ForegroundColor Red
        Write-Host "  Status: Not running" -ForegroundColor Gray
        return $false
    }
}

# Function to test HTTP endpoint
function Test-HttpEndpoint {
    param (
        [string]$Url,
        [string]$ServiceName
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  HTTP: Responding (Status $($response.StatusCode))" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  HTTP: Not responding" -ForegroundColor Yellow
        return $false
    }
}

# Check Backend
Write-Host "Backend Service" -ForegroundColor Cyan
Write-Host "---------------" -ForegroundColor Cyan
$backendRunning = Test-Port -Port 8000 -ServiceName "Backend"

if ($backendRunning) {
    Write-Host "  Testing HTTP endpoint..." -ForegroundColor Gray
    $backendResponding = Test-HttpEndpoint -Url "http://localhost:8000/health" -ServiceName "Backend"
    
    if ($backendResponding) {
        Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    }
}

Write-Host ""

# Check Frontend
Write-Host "Frontend Service" -ForegroundColor Cyan
Write-Host "----------------" -ForegroundColor Cyan
$frontendRunning = Test-Port -Port 8501 -ServiceName "Frontend"

if ($frontendRunning) {
    Write-Host "  Testing HTTP endpoint..." -ForegroundColor Gray
    $frontendResponding = Test-HttpEndpoint -Url "http://localhost:8501" -ServiceName "Frontend"
    
    if ($frontendResponding) {
        Write-Host "  URL: http://localhost:8501" -ForegroundColor Cyan
    }
}

Write-Host ""

# Check Python processes
Write-Host "Python Processes" -ForegroundColor Cyan
Write-Host "----------------" -ForegroundColor Cyan

try {
    $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
    
    if ($pythonProcesses) {
        $dashboardProcesses = @()
        
        foreach ($proc in $pythonProcesses) {
            try {
                $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                
                if ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*streamlit*") {
                    $dashboardProcesses += $proc
                    
                    $type = "Unknown"
                    if ($cmdLine -like "*uvicorn*") { $type = "Backend (uvicorn)" }
                    if ($cmdLine -like "*streamlit*") { $type = "Frontend (streamlit)" }
                    
                    Write-Host "  PID $($proc.Id): $type" -ForegroundColor Gray
                    Write-Host "    Memory: $([math]::Round($proc.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor DarkGray
                }
            } catch {
                # Ignore errors for individual processes
            }
        }
        
        if ($dashboardProcesses.Count -eq 0) {
            Write-Host "  No dashboard processes found" -ForegroundColor Yellow
        } else {
            Write-Host ""
            Write-Host "  Total dashboard processes: $($dashboardProcesses.Count)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  No Python processes running" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Could not check Python processes" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $backendRunning -and $frontendRunning

if ($allGood) {
    Write-Host "✓ All services are running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard: http://localhost:8501" -ForegroundColor Cyan
    Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
} else {
    Write-Host "⚠ Some services are not running" -ForegroundColor Yellow
    Write-Host ""
    
    if (-not $backendRunning) {
        Write-Host "  Backend is not running" -ForegroundColor Red
    }
    if (-not $frontendRunning) {
        Write-Host "  Frontend is not running" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "To start services, run:" -ForegroundColor Gray
    Write-Host "  .\run_local.ps1" -ForegroundColor Cyan
    Write-Host "or" -ForegroundColor Gray
    Write-Host "  .\restart_services.ps1" -ForegroundColor Cyan
}

Write-Host ""
