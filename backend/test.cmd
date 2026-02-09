@echo off
echo Test script started at %date% %time% > C:\Project\AZ-Cost\backend\logs\test.log
echo HTTP_PLATFORM_PORT=%HTTP_PLATFORM_PORT% >> C:\Project\AZ-Cost\backend\logs\test.log
timeout /t 300 /nobreak
