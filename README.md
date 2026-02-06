# Azure Cost Dashboard

Authentication-ready, multi-subscription Azure cost optimization dashboard.

## Services

* **Backend**: FastAPI (Port 8000)
* **Frontend**: Streamlit (Port 8501)

## Setup

1. **Install Dependencies**:
   ```powershell
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` in the root or `backend/` directory and fill in details.
   - `AZURE_AUTH_MODE`: Set to `CLI` or `SERVICE_PRINCIPAL`
   - `AZURE_SUBSCRIPTION_IDS`: Optional, comma-separated list

3. **Run Locally**:
   ```powershell
   ./run_local.ps1
   ```

## IIS Deployment

1. Install Python 3.10+ and `wfastcgi` on the server.
2. Enable CGI feature in IIS.
3. Copy the `backend` folder to the IIS site.
4. Ensure `web.config` points to the correct Python executable path.
5. Create an IIS Application pointing to the `backend` folder.
