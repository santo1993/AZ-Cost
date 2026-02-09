# Zombie Days Default Change - Fix for Data Mismatch

## Summary
Changed the default `zombie_days` threshold from **90 days to 30 days** in the Savings Dashboard to match the backend default and eliminate data mismatch between Global Dashboard and Savings Dashboard.

## Problem
- **Global Dashboard** showed: $16,067.47 with 835 items
- **Savings Dashboard** showed: $15,901.12 with 812 items  
- **Difference**: $166.35 and 23 items missing

## Root Cause
The mismatch occurred because:
1. Backend default for `zombie_days` is **30 days**
2. Savings Dashboard frontend default was **90 days**
3. Global Dashboard showed ALL items from scan (created with 30-day threshold)
4. Savings Dashboard filtered out items with `days_inactive < 90` (23 items between 30-89 days)

## Changes Made

### File: `frontend/pages/2_💰_Savings_Dashboard.py`

#### Change 1: Updated selectbox default index
```python
# BEFORE
index=3,  # Default to 90 days (0, 30, 60, 90 is index 3)

# AFTER
index=1,  # Default to 30 days (0, 30, 60, 90 is index 1)
```

#### Change 2: Updated function parameter default
```python
# BEFORE
def get_cached_savings_data(zombie_days: int = 90):

# AFTER
def get_cached_savings_data(zombie_days: int = 30):
```

#### Change 3: Updated session state default
```python
# BEFORE
current_zombie = st.session_state.get("zombie_days_input", 90)

# AFTER
current_zombie = st.session_state.get("zombie_days_input", 30)
```

#### Change 4: Updated cache lookup default
```python
# BEFORE
last_zombie_days = st.session_state.get("last_zombie_days", 90)

# AFTER
last_zombie_days = st.session_state.get("last_zombie_days", 30)
```

## Expected Result
After this change:
- **Both dashboards will now show consistent data** when using default settings
- Savings Dashboard will default to 30 days, matching the backend scan default
- Users can still select different thresholds (0, 30, 60, 90, 180, 365 days) if needed
- The 23 items (disks/snapshots between 30-89 days old) will now be included by default

## Testing
To verify the fix:
1. Clear all caches and restart the application
2. Run a new scan (or use existing scan with 30-day threshold)
3. Check Global Dashboard - note the total savings and count
4. Check Savings Dashboard (with default 30 days selected) - should match Global Dashboard
5. Change Savings Dashboard to 90 days - should show fewer items (as expected)

## Additional Notes
- The backend default remains at 30 days (`backend/app/services/orphaned_service.py`, line 23)
- Users can still filter by different thresholds in the Savings Dashboard UI
- This change only affects the **default** value, not the available options
