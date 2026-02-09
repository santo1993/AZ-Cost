# 🗑️ Cache Management - Quick Reference

## Where to Find It
**Location**: Home page → Left Sidebar → Scroll down to "🗑️ Cache Management"

---

## Quick Actions

### 🧹 Clear Frontend Cache
**What**: Clears browser/session cache  
**When**: Data looks stale, after filter changes  
**Effect**: Page reloads immediately  
**Safe**: ✅ Yes, no data loss

### 🔄 Clear Backend Cache
**What**: Clears server memory cache  
**When**: Need fresh Azure data  
**Effect**: Next API call fetches from Azure  
**Safe**: ✅ Yes, no data loss

### 🗑️ Delete Old Scans
**What**: Removes old scan files from disk  
**When**: Low disk space, cleanup  
**Effect**: Frees disk space  
**Safe**: ⚠️ Permanent deletion

---

## Common Scenarios

### Scenario 1: Data Doesn't Match Azure Portal
```
1. Click "🔄 Clear Backend Cache"
2. Click "🧹 Clear Frontend Cache"
3. Run a new scan
```

### Scenario 2: Dashboard is Slow
```
1. Expand "🗂️ Manage Scan History"
2. Set "Keep most recent scans" to 5
3. Click "🗑️ Delete Old Scans"
```

### Scenario 3: Need Fresh Data
```
1. Click "🔄 Clear Backend Cache"
2. Wait for next data load
```

### Scenario 4: Remove Specific Scan
```
1. Expand "🗂️ Manage Scan History"
2. Find the scan in the list
3. Click 🗑️ button next to it
```

---

## What Gets Deleted?

| Action | Frontend Cache | Backend Cache | Scan Files |
|--------|---------------|---------------|------------|
| Clear Frontend Cache | ✅ | ❌ | ❌ |
| Clear Backend Cache | ❌ | ✅ | ❌ |
| Delete Old Scans | ❌ | ❌ | ✅ |
| Delete Specific Scan | ❌ | ❌ | ✅ (1 file) |

---

## Safety Tips

✅ **Safe to do anytime**:
- Clear Frontend Cache
- Clear Backend Cache

⚠️ **Think before doing**:
- Delete Old Scans (permanent)
- Delete Specific Scan (permanent)

💡 **Best Practice**:
- Keep 5-10 recent scans
- Delete old scans monthly
- Clear caches when troubleshooting

---

## Disk Space Savings

**Small Environment** (10 subscriptions):
- Each scan: ~1.5 MB
- 10 scans: ~15 MB
- Keep 5 scans: Save ~7.5 MB

**Large Environment** (75 subscriptions):
- Each scan: ~5 MB
- 10 scans: ~50 MB
- Keep 5 scans: Save ~25 MB

---

## Troubleshooting

**Problem**: Can't see Cache Management section  
**Solution**: Scroll down in the sidebar

**Problem**: Delete button doesn't work  
**Solution**: Check backend is running at http://localhost:8000

**Problem**: "Failed to clear cache" error  
**Solution**: Restart backend service

**Problem**: Deleted scan still shows  
**Solution**: Click "🧹 Clear Frontend Cache"

---

## Need More Help?

📖 **Full Documentation**: See `CACHE_MANAGEMENT_GUIDE.md`  
🔧 **Technical Details**: See `CACHE_MANAGEMENT_IMPLEMENTATION.md`  
🌐 **API Docs**: http://localhost:8000/docs (when backend is running)

---

## Version
Feature added: February 2024  
Compatible with: Dashboard v1.0+
