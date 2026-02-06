# 💸 Azure Cost Optimization Dashboard

A powerful, interactive dashboard to visualize Azure implementation costs, identify savings opportunities, and optimize your cloud spend.

## 🚀 Key Features

*   **Global Dashboard**: High-level overview of total spend across all subscriptions.
*   **Savings Recommendations**: Automatically detects and quantifies savings from:
    *   **Orphaned Resources**: Disks, NICs, Public IPs not attached to any VM.
    *   **Zombie Resources**: Resources inactive for >90 days.
    *   **Idle Load Balancers**: LBs with no backend targets.
    *   **Underutilized VMs**: (Optional) Scans for VMs with low CPU/Memory usage.
    *   **Azure Advisor**: Integrating official Azure recommendations.
*   **Cost History**: Interactive 12-month cost history with service-level breakdown.
*   **Resource Explorer**: Deep dive into individual resource costs.
*   **Export**: Download all findings as CSV for reporting.

## 🛠️ Prerequisites

*   **Python 3.10** or higher
*   **Azure CLI** (`az login` recommended)
*   Access to Azure Subscriptions (Reader role minimum)

## 📦 Setup Guide

### 1. Installation

Clone the repository and install dependencies for both backend and frontend:

```powershell
# Install Backend Dependencies
pip install -r backend/requirements.txt

# Install Frontend Dependencies
pip install -r frontend/requirements.txt
```

### 2. Configuration

1.  Navigate to the `backend` directory.
2.  Copy `.env.example` to create a new `.env` file:
    ```powershell
    copy .env.example .env
    ```
3.  Edit `.env` and configure your settings:
    *   **AZURE_AUTH_MODE**: Set to `CLI` (for local dev) or `SERVICE_PRINCIPAL`.
    *   **AZURE_SUBSCRIPTION_IDS**: (Optional) Comma-separated list of subscription IDs to include. If left empty, it will auto-discover all accessible subscriptions.
    *   **Thresholds**: Customize `ZOMBIE_DAYS_THRESHOLD` etc. as needed.

### 3. Azure Authentication

Ensure you are logged in to Azure via CLI:

```powershell
az login
```

If you have access to multiple tenants, verify you are setting the correct subscription context or relying on the configured list in `.env`.

## ▶️ Running the Application

You can start both the backend and frontend services using the provided helper script:

```powershell
./run_local.ps1
```

Or run them manually in separate terminals:

**Backend (FastAPI)**:
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
_Backend runs at http://localhost:8000_

**Frontend (Streamlit)**:
```powershell
cd frontend
streamlit run app.py --server.port 8501
```
_Frontend runs at http://localhost:8501_

## 🏗️ Project Structure

*   **/backend**: FastAPI application handling Azure API logic, caching, and data processing.
*   **/frontend**: Streamlit application for the user interface.
*   **/backend/app/services**: Core logic for cost fetching (Cost Management API), resource discovery (Resource Graph), and anomaly detection.

## 📝 Troubleshooting

*   **Timeout Errors**: If you have many subscriptions (50+), the initial load might be slow. Configure `AZURE_SUBSCRIPTION_IDS` in `.env` to limit scope or allow time for the cache to warm up.
*   **$0 Costs**: Ensure your user/SPN has `Cost Management Reader` permissions on the subscriptions.
