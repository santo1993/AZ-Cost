"""
Backend API Client with Caching.
"""
import requests
import streamlit as st
from config import BACKEND_URL
from typing import Dict, Any, List, Optional

class ApiClient:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Dict[str, Any] = None, timeout: int = 300) -> Any:
        try:
            url = f"{self.base_url}/api{endpoint}"
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            st.warning(f"Request timed out for {endpoint}. The Azure API may be slow. Try again later.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"API Error ({endpoint}): {e}")
            return None

    def get_savings_summary(self, subscription_ids: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/savings-summary", params) or {}

    def get_resources(self, subscription_ids: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        params = {"limit": limit}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/resources", params, timeout=60) or []

    def get_advisor_recommendations(self, subscription_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/advisor", params, timeout=60) or []

    def get_orphaned_resources(self, subscription_ids: Optional[str] = None, zombie_days: int = 30, include_costs: bool = True) -> List[Dict[str, Any]]:
        params = {"zombie_days": zombie_days, "include_costs": include_costs}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/orphaned", params, timeout=90) or []

    def get_underutilized_vms(self, subscription_ids: Optional[str] = None, cpu_threshold: float = 5.0, days: int = 7) -> List[Dict[str, Any]]:
        params = {"cpu_threshold": cpu_threshold, "days": days}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/underutilized-vms", params, timeout=360) or []  # 6 min timeout for full VM scan

    
    def get_subscription_costs(self, subscription_ids: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Fetch total costs by subscription."""
        params = {"days": days}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        # Timeout needs to be high for 75+ subscriptions
        return self._get("/costs", params, timeout=180) or {"subscriptions": [], "total": 0.0}

    def get_costs_by_resource_group(self, subscription_ids: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        params = {"days": days}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/costs/by-resource-group", params, timeout=60) or []

    
    def get_monthly_cost_history(self, subscription_ids: Optional[str] = None, months: int = 12) -> Dict[str, Any]:
        """Fetch monthly cost history."""
        params = {"months": months}
        if subscription_ids:
             params["subscription_ids"] = subscription_ids
        return self._get("/costs/monthly-history", params, timeout=60) or {"months": [], "services": [], "data": []}

    # Scan Management
    def start_scan(self) -> Dict[str, Any]:
        """Trigger a new background scan."""
        return self._post("/scans/start", timeout=10)
        
    def get_scan_status(self) -> Dict[str, Any]:
        """Get status of current running scan."""
        return self._get("/scans/status", timeout=5)
        
    def list_scans(self) -> List[Dict[str, Any]]:
        """List historical scans."""
        return self._get("/scans", timeout=10) or []
        
    def get_scan_data(self, scan_id: str) -> Dict[str, Any]:
        """Get full data for a specific scan."""
        return self._get(f"/scans/{scan_id}", timeout=30)

    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """Get list of all subscriptions with names and IDs."""
        return self._get("/subscriptions") or []

api_client = ApiClient()

# =============================================
# CACHED WRAPPER FUNCTIONS
# Cache persists until "Refresh Data" is clicked
# No TTL = data stays cached until manual refresh
# =============================================

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_savings_summary(subscription_ids: Optional[str] = None) -> Dict[str, Any]:
    return api_client.get_savings_summary(subscription_ids)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_resources(subscription_ids: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
    return api_client.get_resources(subscription_ids, limit)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_advisor_recommendations(subscription_ids: Optional[str] = None) -> List[Dict[str, Any]]:
    return api_client.get_advisor_recommendations(subscription_ids)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_orphaned_resources(subscription_ids: Optional[str] = None, zombie_days: int = 30, include_costs: bool = True) -> List[Dict[str, Any]]:
    return api_client.get_orphaned_resources(subscription_ids, zombie_days, include_costs)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_underutilized_vms(subscription_ids: Optional[str] = None, cpu_threshold: float = 5.0, days: int = 7) -> List[Dict[str, Any]]:
    return api_client.get_underutilized_vms(subscription_ids, cpu_threshold, days)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_costs(subscription_ids: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    return api_client.get_subscription_costs(subscription_ids, days)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_costs_by_resource_group(subscription_ids: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
    return api_client.get_costs_by_resource_group(subscription_ids, days)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_monthly_cost_history(subscription_ids: Optional[str] = None, months: int = 12) -> Dict[str, Any]:
    return api_client.get_monthly_cost_history(subscription_ids, months)

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def cached_get_subscriptions() -> List[Dict[str, Any]]:
    return api_client.get_subscriptions()

@st.cache_data(show_spinner=False)  # No TTL - persists until refresh
def get_subscription_name_map() -> Dict[str, str]:
    """Returns a dict mapping subscription_id -> subscription_name."""
    try:
        subs = api_client.get_subscriptions()
        return {s.get("subscription_id", ""): s.get("display_name", s.get("subscription_id", "Unknown")) for s in subs}
    except:
        return {}
