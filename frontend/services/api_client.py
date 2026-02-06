"""
Backend API Client.
"""
import requests
import streamlit as st
from config import BACKEND_URL
from typing import Dict, Any, List, Optional

class ApiClient:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        try:
            url = f"{self.base_url}/api{endpoint}"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
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
        return self._get("/resources", params) or []

    def get_advisor_recommendations(self, subscription_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/advisor", params) or []

    def get_orphaned_resources(self, subscription_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/orphaned", params) or []

    def get_costs(self, subscription_ids: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        params = {"days": days}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/costs", params) or {"subscriptions": [], "total": 0.0}

    def get_costs_by_resource_group(self, subscription_ids: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        params = {"days": days}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/costs/by-resource-group", params) or []

    def get_monthly_cost_history(self, subscription_ids: Optional[str] = None, months: int = 12) -> Dict[str, Any]:
        params = {"months": months}
        if subscription_ids:
            params["subscription_ids"] = subscription_ids
        return self._get("/costs/monthly-history", params) or {"months": [], "services": [], "data": []}

api_client = ApiClient()
