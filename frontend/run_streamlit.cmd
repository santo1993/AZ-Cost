@echo off
echo Starting Streamlit at %date% %time% >> C:\Project\AZ-Cost\frontend\logs\startup.log
echo HTTP_PLATFORM_PORT=%HTTP_PLATFORM_PORT% >> C:\Project\AZ-Cost\frontend\logs\startup.log
cd /d C:\Project\AZ-Cost\frontend
"C:\Program Files\Python313\python.exe" -m streamlit run app.py --server.port %HTTP_PLATFORM_PORT% --server.headless true --server.enableCORS false --server.enableXsrfProtection false 2>> C:\Project\AZ-Cost\frontend\logs\startup.log
