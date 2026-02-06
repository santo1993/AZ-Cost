"""
Savings & Recommendations Router.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from ...services.advisor_service import advisor_service
from ...services.orphaned_service import orphaned_service
from ...services.savings_service import savings_service
from ...models.resource import OptimizationIssue
from ...cache.memory_cache import memory_cache
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/advisor", response_model=List[OptimizationIssue])
async def get_advisor_recommendations(
    subscription_ids: Optional[str] = Query(None),
    force_refresh: bool = False
):
    """Get Azure Advisor cost recommendations."""
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"advisor:{subs}"
    
    return await memory_cache.get_or_set(
        cache_key, 
        lambda: advisor_service.get_recommendations(subs),
        force_refresh
    )

@router.get("/orphaned", response_model=List[OptimizationIssue])
async def get_orphaned_resources(
    subscription_ids: Optional[str] = Query(None),
    force_refresh: bool = False
):
    """Get detected orphaned/zombie resources."""
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"orphaned:{subs}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: orphaned_service.detect_orphaned_resources(subs),
        force_refresh
    )

@router.get("/savings-summary", response_model=Dict[str, Any])
async def get_savings_summary(
    subscription_ids: Optional[str] = Query(None),
    force_refresh: bool = False
):
    """Get aggregated savings summary."""
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"savings_summary:{subs}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: savings_service.get_savings_summary(subs),
        force_refresh
    )
