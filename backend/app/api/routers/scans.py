"""
API Router for Scans.
Manages background scans and partial data retrieval.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from ...services.scan_service import scan_service
from ...services.cost_service import cost_service
from ...services.orphaned_service import orphaned_service
from ...services.advisor_service import advisor_service
from ...services.underutilized_vm_service import underutilized_vm_service
from ...services.subscription_service import subscription_service
from ...utils.logger import get_logger

router = APIRouter(prefix="/scans", tags=["scans"])
logger = get_logger(__name__)

# Global state to track current running scan
current_scan = {
    "scan_id": None,
    "status": "idle", # idle, running, completed, partially_completed, failed
    "progress": 0,
    "current_stage": "",
    "start_time": None,
    "error": None
}

async def run_full_scan(scan_id: str):
    """
    Background task to run a full scan of all modules.
    """
    global current_scan
    current_scan["status"] = "running"
    current_scan["scan_id"] = scan_id
    current_scan["progress"] = 0
    current_scan["error"] = None
    current_scan["start_time"] = datetime.utcnow().isoformat()
    
    data = {}
    
    try:
        # Determine Data Source
        use_export = current_scan.get("mode") == "export"
        
        if use_export:
             logger.info(f"Scan {scan_id}: Starting in EXPORT mode (Blob Storage)")
             from ...services.export_service import cost_export_service
             import asyncio
             
             # 1. Fetch & Parse Export (Offloaded to Thread to prevent blocking)
             current_scan["current_stage"] = "Starting Export Download..."
             current_scan["progress"] = 0
             
             def update_progress(percent, stage):
                 current_scan["progress"] = percent
                 current_scan["current_stage"] = stage
             
             # Run blocking download/parse in separate thread
             export_data = await asyncio.to_thread(cost_export_service.get_latest_data, update_progress)
             
             # Map Export Data to Scan Schema
             data["costs"] = {
                 "total": export_data["total_cost"],
                 "currency": export_data["currency"],
                 "subscriptions": export_data["subscriptions"],
                 "history": export_data["history"]
             }
             
             # Extract Subscriptions from Export
             subs_from_export = [s["subscription_id"] for s in export_data["subscriptions"]]
             subs = subs_from_export
             data["total_subscriptions"] = len(subs)
             current_scan["progress"] = 90
             current_scan["current_stage"] = "Finalizing..."
             logger.info(f"Scan {scan_id}: Parsed {len(subs)} subscriptions from export")
             
        else:
            # ORIGINAL LIVE MODE
            # 1. Subscriptions
            current_scan["current_stage"] = "Discovering Subscriptions (API)..."
            subs = await subscription_service.get_subscriptions()
            data["total_subscriptions"] = len(subs)
            current_scan["progress"] = 10
            logger.info(f"Scan {scan_id}: Found {len(subs)} subscriptions")
            
            # 2. Costs
            current_scan["current_stage"] = "Fetching Costs (API)..."
            costs = await cost_service.get_subscription_costs(subs, days=30)
            data["costs"] = costs
            current_scan["progress"] = 40
            logger.info(f"Scan {scan_id}: Costs fetched")
            
        # 3. Orphaned Resources (Always checks live resources, as exports are cost-only usually)
        # Note: We can pass the costs from export to orphaned service to calculate savings?
        # Orphaned service fetches its own costs currently. 
        current_scan["current_stage"] = "Detecting Orphaned Resources..."
        orthaned_issues = await orphaned_service.detect_orphaned_resources(subs, zombie_days=0)

        data["orphaned"] = orthaned_issues
        current_scan["progress"] = 60
        logger.info(f"Scan {scan_id}: Orphaned resources detected")
        
        # 4. Advisor
        current_scan["current_stage"] = "Fetching Advisor Recommendations..."
        advisor_issues = await advisor_service.get_recommendations(subs)
        data["advisor"] = advisor_issues
        current_scan["progress"] = 80
        logger.info(f"Scan {scan_id}: Advisor recommendations fetched")
        
        # 5. Underutilized VMs (Only if user opts in? For now we'll do it as it's part of full scan)
        # Note: This is slow, maybe skip or limit? Let's run it since we added batching
        current_scan["current_stage"] = "Scanning for Underutilized VMs..."
        vm_issues = await underutilized_vm_service.detect_underutilized_vms(subs)
        
        data["savings_summary"] = {
            "total_potential_monthly_savings": 0.0,
            "components": {}
        }
        
        # Combine issues for savings calculation
        all_issues = orthaned_issues + advisor_issues + vm_issues
        
        # Helper to sum up
        orphaned_savings = sum(i.potential_savings for i in orthaned_issues)
        advisor_savings = sum(i.potential_savings for i in advisor_issues)
        vm_savings = sum(i.potential_savings for i in vm_issues)
        
        data["savings_summary"]["total_potential_monthly_savings"] = orphaned_savings + advisor_savings + vm_savings
        data["savings_summary"]["components"] = {
            "orphaned": orphaned_savings,
            "advisor": advisor_savings,
            "underutilized_vms": vm_savings
        }
        
        # Save to disk
        scan_service.save_scan(scan_id, data)
        
        current_scan["status"] = "completed"
        current_scan["progress"] = 100
        current_scan["current_stage"] = "Completed"
        logger.info(f"Scan {scan_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        current_scan["status"] = "failed"
        current_scan["error"] = str(e)
        import traceback
        logger.error(traceback.format_exc())

@router.post("/start")
async def start_scan(background_tasks: BackgroundTasks, mode: str = "live"):
    """
    Start a new background scan.
    mode: 'live' (default) or 'export' (from blob storage)
    """
    global current_scan
    if current_scan["status"] == "running":
        return {"status": "error", "message": "Scan already in progress", "scan_id": current_scan["scan_id"]}
        
    scan_id = scan_service.create_scan_id()
    
    # Store mode in current scan state for UI visibility
    current_scan["mode"] = mode
    
    # Trigger background task
    background_tasks.add_task(run_full_scan, scan_id)
    
    return {"status": "started", "scan_id": scan_id, "mode": mode}

@router.get("/status")
async def get_scan_status():
    """Get status of current running scan."""
    return current_scan

@router.get("/")
def list_scans():
    """List historical scans."""
    return scan_service.list_scans()

@router.get("/{scan_id}")
def get_scan(scan_id: str):
    """Get full data for a scan."""
    data = scan_service.load_scan(scan_id)
    if not data:
        raise HTTPException(status_code=404, message="Scan not found")
    return data
