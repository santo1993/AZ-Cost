# Manage Services - Azure Cost Dashboard
# Unified script to start, stop, restart, and check services

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "kill")]
    [string]$Action = "start",
    
    [Parameter()]
    [switch]$Background,
    
    [Parameter()]
    [switch]$Install
)

# Set up paths
$rootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"
$logsPath = Join-Path $rootPath "logs"

# Function to check if port is in use
function Test-Port {
    param([int]$Port)
    $processInfo = netstat -ano | Select-String ":$Port" | Select-String "LISTENING"
    return $processInfo
}

# Function to stop service by port
function Stop-ServiceByPort {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    
    $processInfos = netstat -ano | Select-String ":$Port" | Select-String "LISTENING"
    
    if ($processInfos) {
        $pidsToStop = @()
        
        foreach ($processInfo in $processInfos) {
            if ($processInfo -match '\s+(\d+)\s*$') {
                $processId = $matches[1]
                if ($processId -notin $pidsToStop -and $processId -ne 0) {
                    # Verify process actually exists
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        $pidsToStop += $processId
                    }
                }
            }
        }
        
        if ($pidsToStop.Count -gt 0) {
            Write-Host "Stopping $ServiceName (Port $Port)..." -ForegroundColor Yellow
            $successCount = 0
            $failCount = 0
            
            foreach ($processId in $pidsToStop) {
                Write-Host "  Stopping PID: $processId" -ForegroundColor Gray
                
                try {
                    Stop-Process -Id $processId -Force -ErrorAction Stop
                    $successCount++
                    Write-Host "    + Stopped" -ForegroundColor Green
                } catch {
                    # Try taskkill as fallback
                    try {
                        $result = taskkill /F /PID $processId 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            $successCount++
                            Write-Host "    + Stopped (using taskkill)" -ForegroundColor Green
                        } else {
                            $failCount++
                            Write-Host "    X Failed" -ForegroundColor Red
                        }
                    } catch {
                        $failCount++
                        Write-Host "    X Failed" -ForegroundColor Red
                    }
                }
            }
            
            if ($successCount -gt 0) {
                Write-Host "  + $ServiceName stopped ($successCount process(es))" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  X Failed to stop $ServiceName" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "$ServiceName (Port $Port) - No active processes found" -ForegroundColor Gray
            return $false
        }
    } else {
        Write-Host "$ServiceName (Port $Port) is not running" -ForegroundColor Gray
        return $false
    }
}

# Function to start services
function Start-Services {
    param([bool]$RunInBackground)
    
    Write-Host "Starting Azure Cost Dashboard..." -ForegroundColor Cyan
    Write-Host ""
    
    # Check if services are already running
    $backendRunning = Test-Port -Port 8000
    $frontendRunning = Test-Port -Port 8501
    
    if ($backendRunning -or $frontendRunning) {
        Write-Host "Services are already running:" -ForegroundColor Yellow
        if ($backendRunning) { Write-Host "  - Backend (Port 8000)" -ForegroundColor Yellow }
        if ($frontendRunning) { Write-Host "  - Frontend (Port 8501)" -ForegroundColor Yellow }
        Write-Host ""
        
        $response = Read-Host "Restart them? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Gray
            return
        }
        
        Write-Host ""
        Stop-ServiceByPort -Port 8000 -ServiceName "Backend"
        Stop-ServiceByPort -Port 8501 -ServiceName "Frontend"
        Start-Sleep -Seconds 2
        Write-Host ""
    }
    
    if ($RunInBackground) {
        # Create logs directory
        if (-not (Test-Path $logsPath)) {
            New-Item -ItemType Directory -Path $logsPath | Out-Null
        }
        
        # Start Backend in background
        Write-Host "Starting Backend (Port 8000) in background..." -ForegroundColor Green
        $backendLog = Join-Path $logsPath "backend.log"
        $backendErrorLog = Join-Path $logsPath "backend_error.log"
        
        $backendProcess = Start-Process -FilePath "python" `
            -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" `
            -WorkingDirectory $backendPath `
            -WindowStyle Hidden `
            -RedirectStandardOutput $backendLog `
            -RedirectStandardError $backendErrorLog `
            -PassThru
        
        Write-Host "  PID: $($backendProcess.Id)" -ForegroundColor Gray
        Write-Host "  Log: $backendLog" -ForegroundColor Gray
        
        # Wait for backend
        Write-Host "  Waiting for backend to start..." -ForegroundColor Gray
        $maxAttempts = 30
        $attempt = 0
        $backendReady = $false
        
        while ($attempt -lt $maxAttempts -and -not $backendReady) {
            Start-Sleep -Seconds 1
            $attempt++
            
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $backendReady = $true
                }
            } catch {
                Write-Host "." -NoNewline -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        if ($backendReady) {
            Write-Host "  + Backend is ready!" -ForegroundColor Green
        } else {
            Write-Host "  ! Backend did not respond within 30 seconds" -ForegroundColor Yellow
            Write-Host "    Check logs: $backendLog" -ForegroundColor Gray
        }
        
        Write-Host ""
        
        # Start Frontend in background
        Write-Host "Starting Frontend (Port 8501) in background..." -ForegroundColor Green
        $frontendLog = Join-Path $logsPath "frontend.log"
        $frontendErrorLog = Join-Path $logsPath "frontend_error.log"
        
        $frontendProcess = Start-Process -FilePath "python" `
            -ArgumentList "-m streamlit run app.py --server.port 8501 --server.headless true" `
            -WorkingDirectory $frontendPath `
            -WindowStyle Hidden `
            -RedirectStandardOutput $frontendLog `
            -RedirectStandardError $frontendErrorLog `
            -PassThru
        
        Write-Host "  PID: $($frontendProcess.Id)" -ForegroundColor Gray
        Write-Host "  Log: $frontendLog" -ForegroundColor Gray
        Write-Host "  + Frontend starting..." -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Logs directory: $logsPath" -ForegroundColor Gray
        
    } else {
        # Start in foreground
        Write-Host "Starting Backend (Port 8000)..." -ForegroundColor Green
        Start-Process -FilePath "python" `
            -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" `
            -WorkingDirectory $backendPath `
            -NoNewWindow
        
        Write-Host "  + Backend starting..." -ForegroundColor Green
        Start-Sleep -Seconds 5
        
        Write-Host ""
        Write-Host "Starting Frontend (Port 8501)..." -ForegroundColor Green
        Start-Process -FilePath "python" `
            -ArgumentList "-m streamlit run app.py --server.port 8501" `
            -WorkingDirectory $frontendPath `
            -NoNewWindow
        
        Write-Host "  + Frontend starting..." -ForegroundColor Green
    }
    
    # Summary
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Services Started!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dashboard:  http://localhost:8501" -ForegroundColor Cyan
    Write-Host "API:        http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "Health:     http://localhost:8000/health" -ForegroundColor Cyan
    Write-Host ""
    
    if ($RunInBackground) {
        Write-Host "Services are running in background." -ForegroundColor Gray
        Write-Host "Use '.\manage.ps1 logs' to view logs" -ForegroundColor Gray
        Write-Host "Use '.\manage.ps1 stop' to stop services" -ForegroundColor Gray
    } else {
        Write-Host "Services are running in foreground." -ForegroundColor Gray
        Write-Host "Press Ctrl+C in the service windows to stop them." -ForegroundColor Gray
    }
    Write-Host ""
}

# Function to force kill all dashboard processes
function Force-KillDashboard {
    Write-Host "Force killing all dashboard processes..." -ForegroundColor Yellow
    Write-Host ""
    
    $killedCount = 0
    $pidsKilled = @()
    
    # Kill by port
    $ports = @(8000, 8501)
    foreach ($port in $ports) {
        $processInfos = netstat -ano | Select-String ":$port" | Select-String "LISTENING"
        
        if ($processInfos) {
            foreach ($processInfo in $processInfos) {
                if ($processInfo -match '\s+(\d+)\s*$') {
                    $processId = $matches[1]
                    
                    # Skip if already killed or PID is 0
                    if ($processId -in $pidsKilled -or $processId -eq 0) {
                        continue
                    }
                    
                    # Verify process exists
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if (-not $process) {
                        Write-Host "Process on port $port (PID: $processId) - Already stopped" -ForegroundColor Gray
                        continue
                    }
                    
                    Write-Host "Killing process on port $port (PID: $processId)..." -ForegroundColor Yellow
                    
                    $result = taskkill /F /PID $processId 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "  + Killed" -ForegroundColor Green
                        $killedCount++
                        $pidsKilled += $processId
                    } else {
                        Write-Host "  X Failed: $result" -ForegroundColor Red
                    }
                }
            }
        }
    }
    
    # Kill Python processes running dashboard
    try {
        $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        
        if ($pythonProcesses) {
            foreach ($proc in $pythonProcesses) {
                # Skip if already killed
                if ($proc.Id -in $pidsKilled) {
                    continue
                }
                
                try {
                    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                    
                    if ($cmdLine -like "*uvicorn*app.main:app*" -or $cmdLine -like "*streamlit*run*app.py*") {
                        Write-Host "Killing dashboard process (PID: $($proc.Id))..." -ForegroundColor Yellow
                        $result = taskkill /F /PID $proc.Id 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host "  + Killed" -ForegroundColor Green
                            $killedCount++
                            $pidsKilled += $proc.Id
                        } else {
                            Write-Host "  X Failed" -ForegroundColor Red
                        }
                    }
                } catch {
                    # Ignore errors
                }
            }
        }
    } catch {
        # Ignore errors
    }
    
    Write-Host ""
    if ($killedCount -gt 0) {
        Write-Host "+ Force killed $killedCount process(es)" -ForegroundColor Green
    } else {
        Write-Host "No dashboard processes found to kill" -ForegroundColor Gray
    }
    Write-Host ""
}
function Stop-Services {
    Write-Host "Stopping Azure Cost Dashboard Services..." -ForegroundColor Cyan
    Write-Host ""
    
    $backendStopped = Stop-ServiceByPort -Port 8000 -ServiceName "Backend"
    $frontendStopped = Stop-ServiceByPort -Port 8501 -ServiceName "Frontend"
    
    Write-Host ""
    
    # Check for remaining dashboard processes
    try {
        $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        
        if ($pythonProcesses) {
            $stoppedCount = 0
            
            foreach ($proc in $pythonProcesses) {
                try {
                    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                    
                    if ($cmdLine -like "*uvicorn*app.main:app*" -or $cmdLine -like "*streamlit*run*app.py*") {
                        Write-Host "Stopping dashboard process (PID: $($proc.Id))..." -ForegroundColor Yellow
                        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                        $stoppedCount++
                    }
                } catch {
                    # Ignore errors
                }
            }
            
            if ($stoppedCount -gt 0) {
                Write-Host "Stopped $stoppedCount additional process(es)" -ForegroundColor Green
            }
        }
    } catch {
        # Ignore errors
    }
    
    Write-Host ""
    if ($backendStopped -or $frontendStopped) {
        Write-Host "+ Services stopped successfully" -ForegroundColor Green
    } else {
        Write-Host "No services were running" -ForegroundColor Gray
    }
    Write-Host ""
}

# Function to show status
function Show-Status {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Azure Cost Dashboard - Status" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check Backend
    Write-Host "Backend Service (Port 8000)" -ForegroundColor Cyan
    Write-Host "---------------------------" -ForegroundColor Cyan
    $backendInfo = Test-Port -Port 8000
    
    if ($backendInfo) {
        # Extract all PIDs
        $pids = @()
        foreach ($line in $backendInfo) {
            if ($line -match '\s+(\d+)\s*$') {
                $procId = $matches[1]
                if ($procId -ne 0 -and $procId -notin $pids) {
                    # Verify process exists
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($proc) {
                        $pids += $procId
                    }
                }
            }
        }
        
        if ($pids.Count -gt 0) {
            Write-Host "+ Running" -ForegroundColor Green
            
            foreach ($processId in $pids) {
                Write-Host "  PID: $processId" -ForegroundColor Gray
                
                try {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "    Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
                    }
                } catch {}
            }
        } else {
            Write-Host "X Not running (stale connections)" -ForegroundColor Red
        }
        
        # Test HTTP endpoint
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  HTTP: Responding (Status $($response.StatusCode))" -ForegroundColor Green
            Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
        } catch {
            Write-Host "  HTTP: Not responding" -ForegroundColor Yellow
        }
    } else {
        Write-Host "X Not running" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Check Frontend
    Write-Host "Frontend Service (Port 8501)" -ForegroundColor Cyan
    Write-Host "----------------------------" -ForegroundColor Cyan
    $frontendInfo = Test-Port -Port 8501
    
    if ($frontendInfo) {
        # Extract all PIDs
        $pids = @()
        foreach ($line in $frontendInfo) {
            if ($line -match '\s+(\d+)\s*$') {
                $procId = $matches[1]
                if ($procId -ne 0 -and $procId -notin $pids) {
                    # Verify process exists
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($proc) {
                        $pids += $procId
                    }
                }
            }
        }
        
        if ($pids.Count -gt 0) {
            Write-Host "+ Running" -ForegroundColor Green
            
            foreach ($processId in $pids) {
                Write-Host "  PID: $processId" -ForegroundColor Gray
                
                try {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "    Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
                    }
                } catch {}
            }
        } else {
            Write-Host "X Not running (stale connections)" -ForegroundColor Red
        }
        
        # Test HTTP endpoint
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  HTTP: Responding (Status $($response.StatusCode))" -ForegroundColor Green
            Write-Host "  URL: http://localhost:8501" -ForegroundColor Cyan
        } catch {
            Write-Host "  HTTP: Not responding" -ForegroundColor Yellow
        }
    } else {
        Write-Host "X Not running" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    
    $allRunning = $backendInfo -and $frontendInfo
    
    if ($allRunning) {
        Write-Host "+ All services are running!" -ForegroundColor Green
    } else {
        Write-Host "! Some services are not running" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

# Function to view logs
function Show-Logs {
    if (-not (Test-Path $logsPath)) {
        Write-Host "Logs directory not found: $logsPath" -ForegroundColor Red
        Write-Host "Services may not have been started in background mode." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To start in background: .\manage.ps1 start -Background" -ForegroundColor Cyan
        return
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Recent Logs (Last 30 lines)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $backendLog = Join-Path $logsPath "backend.log"
    $backendErrorLog = Join-Path $logsPath "backend_error.log"
    $frontendLog = Join-Path $logsPath "frontend.log"
    $frontendErrorLog = Join-Path $logsPath "frontend_error.log"
    
    # Backend logs
    Write-Host "Backend Output:" -ForegroundColor Cyan
    Write-Host "---------------" -ForegroundColor Cyan
    if (Test-Path $backendLog) {
        Get-Content $backendLog -Tail 30
    } else {
        Write-Host "No backend log file found" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Backend Errors:" -ForegroundColor Red
    Write-Host "---------------" -ForegroundColor Red
    if (Test-Path $backendErrorLog) {
        $errorContent = Get-Content $backendErrorLog -Tail 30
        if ($errorContent) {
            $errorContent
        } else {
            Write-Host "No errors" -ForegroundColor Green
        }
    } else {
        Write-Host "No error log file found" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To follow logs in real-time:" -ForegroundColor Gray
    Write-Host "  Get-Content logs\backend.log -Tail 50 -Wait" -ForegroundColor Cyan
    Write-Host "  Get-Content logs\frontend.log -Tail 50 -Wait" -ForegroundColor Cyan
    Write-Host ""
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing Dependencies..." -ForegroundColor Cyan
    Write-Host ""
    
    if (-not (Test-Path "backend/requirements.txt")) {
        Write-Host "X Backend requirements.txt not found" -ForegroundColor Red
        return
    }
    
    if (-not (Test-Path "frontend/requirements.txt")) {
        Write-Host "X Frontend requirements.txt not found" -ForegroundColor Red
        return
    }
    
    Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
    pip install -r backend/requirements.txt
    
    Write-Host ""
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    pip install -r frontend/requirements.txt
    
    Write-Host ""
    Write-Host "+ Dependencies installed successfully" -ForegroundColor Green
    Write-Host ""
}

# Main script logic
Write-Host ""

# Handle install flag
if ($Install) {
    Install-Dependencies
    if ($Action -ne "start") {
        exit 0
    }
}

# Execute action
switch ($Action) {
    "start" {
        Start-Services -RunInBackground $Background
    }
    "stop" {
        Stop-Services
    }
    "restart" {
        Stop-Services
        Start-Sleep -Seconds 2
        Start-Services -RunInBackground $Background
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "kill" {
        Force-KillDashboard
    }
}
