# ✅ CONSOLIDATED SERVICE MANAGEMENT

All service management has been consolidated into **ONE** powerful script: `manage.ps1`

## 🚀 Quick Start

```powershell
# Start services in background
.\manage.ps1 start -Background

# Check status
.\manage.ps1 status

# Stop services
.\manage.ps1 stop
```

## 📋 Available Scripts (Simplified)

| Script | Purpose |
|--------|---------|
| **`manage.ps1`** | ⭐ **All-in-one** - Start, stop, restart, status, logs |
| `run_local.ps1` | Original foreground startup (kept for compatibility) |
| `install_dependencies.ps1` | Install Python dependencies |

## 🎯 All Commands in One Script

### Start Services

```powershell
# Background mode (recommended)
.\manage.ps1 start -Background

# Foreground mode
.\manage.ps1 start

# Install dependencies and start
.\manage.ps1 start -Install -Background
```

### Stop Services

```powershell
.\manage.ps1 stop
```

### Restart Services

```powershell
.\manage.ps1 restart -Background
```

### Check Status

```powershell
.\manage.ps1 status
```

Shows:
- ✅ Which services are running
- 🆔 Process IDs
- 💾 Memory usage
- 🌐 HTTP endpoint status

### View Logs

```powershell
.\manage.ps1 logs
```

Shows recent backend logs and errors.

## 🌐 Access URLs

- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 Fix Your Connection Error

Your original error: `HTTPConnectionPool(host='10.137.3.39', port=8000): Max retries exceeded`

**Solution:**

```powershell
# 1. Start services in background
.\manage.ps1 start -Background

# 2. Wait 15 seconds
Start-Sleep -Seconds 15

# 3. Check status
.\manage.ps1 status

# 4. Test backend
curl http://localhost:8000/health

# 5. If issues, check logs
.\manage.ps1 logs
```

## 📁 File Structure

```
Project/
├── manage.ps1                    # ⭐ Main management script
├── run_local.ps1                 # Original foreground startup
├── install_dependencies.ps1      # Dependency installer
├── QUICKSTART.txt                # Quick reference card
├── QUICK_REFERENCE.md            # Detailed guide
├── SCRIPTS_README.md             # Scripts documentation
└── logs/                         # Log files (created automatically)
    ├── backend.log
    ├── backend_error.log
    ├── frontend.log
    └── frontend_error.log
```

## 🎓 Common Workflows

### First Time Setup

```powershell
.\manage.ps1 start -Install -Background
Start-Sleep -Seconds 15
.\manage.ps1 status
```

### Daily Development

```powershell
# Morning - start services
.\manage.ps1 start -Background

# Check they're running
.\manage.ps1 status

# Evening - stop services
.\manage.ps1 stop
```

### Troubleshooting

```powershell
# Check what's wrong
.\manage.ps1 status
.\manage.ps1 logs

# Restart everything
.\manage.ps1 restart -Background

# Verify it's working
.\manage.ps1 status
curl http://localhost:8000/health
```

## 📚 Documentation Files

- **QUICKSTART.txt** - Quick reference card (print-friendly)
- **QUICK_REFERENCE.md** - Detailed command reference
- **SCRIPTS_README.md** - Scripts documentation
- **README.md** - Main project documentation

## ✨ Benefits of Consolidation

✅ **One script to rule them all** - No confusion about which script to use  
✅ **Consistent interface** - Same script for all operations  
✅ **Less clutter** - Only 3 scripts instead of 8+  
✅ **Easier to maintain** - Changes in one place  
✅ **Better error handling** - Unified error messages  
✅ **Automatic cleanup** - Stops existing services before starting  

## 🆚 Before vs After

### Before (8+ scripts):
- `run_background.ps1`
- `start_dashboard.ps1`
- `start_simple.ps1`
- `start.ps1`
- `stop_services.ps1`
- `check_status.ps1`
- `view_logs.ps1`
- `quick_restart.ps1`
- `run_local.ps1`
- `install_dependencies.ps1`

### After (3 scripts):
- **`manage.ps1`** ⭐ (does everything)
- `run_local.ps1` (kept for compatibility)
- `install_dependencies.ps1` (convenience wrapper)

## 🎯 Remember

**For everything, use:**
```powershell
.\manage.ps1 <action> [options]
```

**Actions:** start | stop | restart | status | logs  
**Options:** -Background | -Install

That's it! 🎉
