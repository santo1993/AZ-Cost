"""
Savings & Recommendations Router.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from ...services.advisor_service import advisor_service
from ...services.orphaned_service import orphaned_service
from ...services.savings_service import savings_service
from ...services.underutilized_vm_service import underutilized_vm_service
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
    zombie_days: int = Query(30, ge=1, le=365, description="Minimum days for zombie resources"),
    include_costs: bool = Query(True, description="Include actual costs from Cost Management (slower)"),
    force_refresh: bool = False
):
    """Get detected orphaned/zombie resources with actual costs."""
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"orphaned:{subs}:{zombie_days}:{include_costs}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: orphaned_service.detect_orphaned_resources(subs, include_costs=include_costs, zombie_days=zombie_days),
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

@router.get("/underutilized-vms", response_model=List[OptimizationIssue])
async def get_underutilized_vms(
    subscription_ids: Optional[str] = Query(None),
    cpu_threshold: float = Query(5.0, ge=1, le=50, description="CPU utilization threshold (%)"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    force_refresh: bool = False
):
    """Get VMs with low CPU/Memory utilization."""
    subs = subscription_ids.split(",") if subscription_ids else None
    cache_key = f"underutilized_vms:{subs}:{cpu_threshold}:{days}"
    
    return await memory_cache.get_or_set(
        cache_key,
        lambda: underutilized_vm_service.detect_underutilized_vms(subs, cpu_threshold=cpu_threshold, days=days),
        force_refresh
    )
