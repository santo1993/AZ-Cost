# Cache Management Guide

## Overview
The Azure Cost Dashboard uses multiple layers of caching to improve performance and reduce API calls to Azure. This guide explains how to manage cached data effectively.

## Cache Layers

### 1. **Frontend Cache (Streamlit)**
- **Location**: Browser memory / Streamlit session state
- **Contains**: 
  - API responses (costs, savings, recommendations)
  - Scan data loaded from backend
  - Subscription mappings
- **Lifetime**: Until page refresh or manual clear
- **Size**: Typically 1-10 MB per session

### 2. **Backend Memory Cache**
- **Location**: Backend server RAM
- **Contains**:
  - Azure API responses (Resource Graph, Cost Management, Advisor)
  - Computed results (orphaned resources, savings calculations)
- **Lifetime**: Configurable TTL (default: 4 hours)
- **Size**: Varies based on subscription count (10-100 MB typical)

### 3. **Scan History (Disk Storage)**
- **Location**: `backend/data/` directory
- **Contains**:
  - Complete snapshots of cost and savings data
  - Historical scan results with timestamps
- **Lifetime**: Permanent until manually deleted
- **Size**: 1-5 MB per scan

## Cache Management UI

### Accessing Cache Management
1. Open the dashboard home page
2. Scroll down in the **left sidebar**
3. Find the **"🗑️ Cache Management"** section

### Available Actions

#### 1. Clear Frontend Cache
**Button**: 🧹 Clear Frontend Cache

**What it does**:
- Clears Streamlit's `@st.cache_data` cache
- Removes session state cached data:
  - `cached_cost_data`
  - `cached_savings_data`
  - `cached_savings_issues`
- Forces reload of data on next page visit

**When to use**:
- After changing subscription filters
- When data appears stale or incorrect
- After backend updates

**Impact**: Immediate page reload

---

#### 2. Clear Backend Cache
**Button**: 🔄 Clear Backend Cache

**What it does**:
- Clears the backend memory cache (TTLCache)
- Forces fresh API calls to Azure on next request
- Does NOT delete scan history

**When to use**:
- After making changes in Azure (new resources, deletions)
- When you need the absolute latest data
- After Azure Advisor generates new recommendations

**Impact**: Next API call will be slower (fetching fresh data)

---

#### 3. Delete Old Scans
**Section**: 🗂️ Manage Scan History (Expandable)

**Options**:
- **Keep most recent scans**: Number input (1-20, default: 5)
- **Delete Old Scans button**: Removes scans older than the keep count

**What it does**:
- Lists all stored scans with timestamps
- Allows bulk deletion of old scans
- Keeps only the N most recent scans
- Frees up disk space

**When to use**:
- When disk space is limited
- To remove outdated historical data
- Regular maintenance (weekly/monthly)

**Example**:
- You have 15 scans
- Set "Keep most recent scans" to 5
- Click "Delete Old Scans"
- Result: 10 oldest scans deleted, 5 newest kept

---

#### 4. Delete Individual Scans
**Location**: Inside "Manage Scan History" expander

**What it does**:
- Shows list of up to 10 most recent scans
- Each scan has a 🗑️ delete button
- Allows selective deletion of specific scans

**When to use**:
- Remove a specific problematic scan
- Delete test scans
- Clean up failed scans

---

## API Endpoints

### Backend Cache Management Endpoints

#### Clear Memory Cache
```http
POST /api/scans/clear-cache
```
**Response**:
```json
{
  "status": "success",
  "message": "Memory cache cleared"
}
```

#### Delete Specific Scan
```http
DELETE /api/scans/{scan_id}
```
**Response**:
```json
{
  "status": "success",
  "message": "Scan 20240209_113509 deleted"
}
```

#### Cleanup Old Scans
```http
POST /api/scans/cleanup-old-scans?keep_count=5
```
**Response**:
```json
{
  "status": "success",
  "message": "Deleted 10 old scans, kept 5 most recent",
  "deleted_count": 10
}
```

---

## Best Practices

### Regular Maintenance Schedule

**Daily**:
- No action needed (cache TTL handles this)

**Weekly**:
- Clear backend cache if you need fresh data
- Review scan count

**Monthly**:
- Delete old scans (keep 5-10 recent ones)
- Clear frontend cache to ensure clean state

### Troubleshooting with Cache Management

#### Problem: Data doesn't match Azure Portal
**Solution**:
1. Clear Backend Cache
2. Clear Frontend Cache
3. Run a new scan

#### Problem: Dashboard is slow
**Solution**:
1. Check scan count (delete old scans if >20)
2. Use cached scan data instead of live API
3. Clear frontend cache to remove stale session data

#### Problem: "Scan not found" error
**Solution**:
1. Clear Frontend Cache
2. Select "Live/Cached Data" from scan selector
3. Run a new scan

#### Problem: Disk space running low
**Solution**:
1. Open "Manage Scan History"
2. Set "Keep most recent scans" to 3-5
3. Click "Delete Old Scans"

---

## Cache Size Estimates

### Typical Environment (10 subscriptions, 1000 resources)
- **Frontend Cache**: ~2 MB per session
- **Backend Memory Cache**: ~20 MB
- **Single Scan**: ~1.5 MB
- **10 Scans**: ~15 MB

### Large Environment (75 subscriptions, 10,000 resources)
- **Frontend Cache**: ~10 MB per session
- **Backend Memory Cache**: ~100 MB
- **Single Scan**: ~5 MB
- **10 Scans**: ~50 MB

---

## Configuration

### Backend Cache TTL
Edit `backend/.env`:
```env
CACHE_TTL_HOURS=4  # Default: 4 hours
```

### Scan Storage Location
Default: `backend/data/`

To change, modify `backend/app/services/scan_service.py`:
```python
scan_service = ScanService(data_dir="custom/path")
```

---

## Automated Cleanup (Optional)

### PowerShell Script for Scheduled Cleanup
Create `cleanup_cache.ps1`:
```powershell
# Keep only 5 most recent scans
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/scans/cleanup-old-scans?keep_count=5" -Method Post
Write-Host "Cleanup result: $($response.message)"
```

Schedule with Task Scheduler (Windows) or cron (Linux).

---

## Security Considerations

- Cache management endpoints require backend access
- No authentication currently implemented
- Consider adding API keys for production deployments
- Scan data may contain sensitive resource information
- Ensure proper file permissions on `backend/data/` directory

---

## FAQ

**Q: Will clearing cache delete my Azure resources?**
A: No. Cache management only affects local data. Azure resources are never modified.

**Q: How often should I clear the cache?**
A: Only when you need fresh data or troubleshooting. The TTL handles automatic expiration.

**Q: Can I recover deleted scans?**
A: No. Scan deletion is permanent. Consider backing up important scans before cleanup.

**Q: Does clearing cache affect other users?**
A: Backend cache is shared. Frontend cache is per-session. Scan deletion affects all users.

**Q: What happens if I delete all scans?**
A: Dashboard will fall back to live API calls. You can create new scans anytime.

---

## Support

For issues or questions:
1. Check logs: `backend/logs/` (if configured)
2. Review backend console output
3. Check browser console (F12) for frontend errors
4. Verify backend is running: `http://localhost:8000/docs`
