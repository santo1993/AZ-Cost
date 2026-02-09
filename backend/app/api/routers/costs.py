"""
Cost API Router.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
from ...services.cost_service import cost_service
from ...cache.memory_cache import memory_cache
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/costs")
async def get_subscription_costs(
    subscription_ids: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get total costs by subscription for the last calendar month.
    Note: 'days' parameter is ignored - always returns last complete month.
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"costs:{subs}:{days}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: cost_service.get_subscription_costs(subs, days),
        force_refresh
    )

@router.get("/costs/by-resource-group")
async def get_costs_by_resource_group(
    subscription_ids: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Get costs grouped by resource group for the last calendar month.
    Note: 'days' parameter is ignored - always returns last complete month.
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"costs_by_rg:{subs}:{days}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: cost_service.get_costs_by_resource_group(subs, days),
        force_refresh
    )

@router.get("/costs/monthly-history")
async def get_monthly_cost_history(
    subscription_ids: Optional[str] = Query(None),
    months: int = Query(12, ge=1, le=24),
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get monthly cost history with breakdown by service type.
    Returns data for stacked bar chart visualization.
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"costs_monthly:{subs}:{months}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: cost_service.get_monthly_cost_history(subs, months),
        force_refresh
    )

@router.get("/costs/by-resource")
async def get_costs_by_resource(
    subscription_ids: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    force_refresh: bool = False
) -> Dict[str, float]:
    """
    Get costs by individual resource ID for the last calendar month.
    Note: 'days' parameter is ignored - always returns last complete month.
    Returns a dict mapping resource_id -> cost.
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"costs_by_resource:{subs}:{days}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: cost_service.get_costs_by_resource(subs, days),
        force_refresh
    )
