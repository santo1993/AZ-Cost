"""
Resources Router.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ...services.resource_discovery import resource_discovery_service
from ...models.resource import Resource
from ...cache.memory_cache import memory_cache
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/resources", response_model=List[Resource])
async def get_resources(
    subscription_ids: Optional[str] = Query(None, description="Comma-separated subscription IDs"),
    resource_types: Optional[str] = Query(None, description="Comma-separated resource types"),
    limit: int = 1000,
    force_refresh: bool = False
):
    """
    Get all resources across subscriptions.
    Cached for performance (TTL 1h default).
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    types = resource_types.split(",") if resource_types else None
    
    # Generate cache key
    cache_key = f"resources:{subs}:{types}:{limit}"
    
    async def fetch_data():
        return await resource_discovery_service.get_all_resources(
            subscription_ids=subs,
            resource_types=types,
            limit=limit
        )
    
    try:
        data = await memory_cache.get_or_set(cache_key, fetch_data, force_refresh)
        return data
    except Exception as e:
        logger.error(f"Error fetching resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions")
async def get_subscriptions(force_refresh: bool = False):
    """
    Get list of all subscriptions with names and IDs.
    """
    from ...services.subscription_service import subscription_service
    
    cache_key = "subscriptions_list_v2"
    
    # Check if already cached
    cached = memory_cache.get(cache_key)
    if cached and not force_refresh:
        return cached
    
    # Fetch fresh data - call internal method directly to bypass service cache
    try:
        sub_details = await subscription_service._fetch_subscription_details()
        if sub_details:
            memory_cache.set(cache_key, sub_details)
            return sub_details
        return []
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions: {e}")
        return []
