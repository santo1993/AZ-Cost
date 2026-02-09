"""
Frontend Configuration.

Supports accessing backend via:
- localhost (default for local development)
- IP address (e.g., http://192.168.1.100:8000)
- Domain name (e.g., http://api.yourdomain.com)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Backend URL - can be localhost, IP address, or domain name
# Examples:
#   - http://localhost:8000 (local development)
#   - http://192.168.1.100:8000 (access via IP)
#   - http://api.yourdomain.com (access via domain)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

print(f"Frontend configured to connect to backend at: {BACKEND_URL}")
