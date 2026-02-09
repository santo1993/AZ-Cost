@echo off
echo ========================================
echo Starting FastAPI Backend
echo ========================================
echo Time: %date% %time% >> C:\Project\AZ-Cost\backend\logs\startup.log
echo HTTP_PLATFORM_PORT=%HTTP_PLATFORM_PORT% >> C:\Project\AZ-Cost\backend\logs\startup.log
echo PYTHONPATH=%PYTHONPATH% >> C:\Project\AZ-Cost\backend\logs\startup.log
echo ========================================

cd /d C:\Project\AZ-Cost\backend

REM Check if HTTP_PLATFORM_PORT is set
if "%HTTP_PLATFORM_PORT%"=="" (
    echo ERROR: HTTP_PLATFORM_PORT not set! >> C:\Project\AZ-Cost\backend\logs\startup.log
    echo ERROR: HTTP_PLATFORM_PORT not set!
    exit /b 1
)

echo Starting uvicorn on port %HTTP_PLATFORM_PORT% >> C:\Project\AZ-Cost\backend\logs\startup.log

REM Start uvicorn with the dynamic port
"C:\Program Files\Python313\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %HTTP_PLATFORM_PORT% --log-level info 2>> C:\Project\AZ-Cost\backend\logs\error.log
