"""
Export Router.
"""
from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional
from ...services.csv_export_service import csv_export_service
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/export-csv")
async def export_resources_csv(
    subscription_ids: Optional[str] = Query(None),
    resource_types: Optional[str] = Query(None)
):
    """
    Stream a CSV export of resources.
    """
    subs = subscription_ids.split(",") if subscription_ids else None
    types = resource_types.split(",") if resource_types else None
    
    stream = csv_export_service.generate_resource_csv_stream(
        subscription_ids=subs,
        resource_types=types
    )
    
    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=azure_resources.csv"}
    )
