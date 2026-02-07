"""
VM Enrichment Service - Background fetcher for VM deallocated timestamps.

This service runs in the background after a scan completes, fetching VM instance views
from Azure Compute API to get the exact "deallocated since" timestamps.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from azure.mgmt.compute import ComputeManagementClient
from ..services.azure_auth import auth_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool for Azure SDK calls (they are sync)
_executor = ThreadPoolExecutor(max_workers=3)

class VMEnrichmentService:
    """Background service to enrich VM data with instance view timestamps."""
    
    def __init__(self):
        self._enrichment_status: Dict[str, str] = {}  # scan_id -> status
    
    def get_status(self, scan_id: str) -> str:
        """Get enrichment status for a scan."""
        return self._enrichment_status.get(scan_id, "not_started")
    
    def _get_vm_instance_view(self, sub_id: str, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """
        Sync method to get VM instance view from Compute API.
        Returns the deallocated timestamp if available.
        """
        try:
            credential = auth_service.get_credential()
            compute_client = ComputeManagementClient(credential, sub_id)
            
            instance_view = compute_client.virtual_machines.instance_view(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            
            # Find the deallocated/stopped status and its time
            for status in instance_view.statuses or []:
                if status.code and ('PowerState/deallocated' in status.code or 'PowerState/stopped' in status.code):
                    if status.time:
                        return {
                            "vm_name": vm_name,
                            "status_time": status.time.isoformat(),
                            "status_code": status.code
                        }
            
            return {"vm_name": vm_name, "status_time": None}
            
        except Exception as e:
            logger.debug(f"Could not get instance view for {vm_name}: {e}")
            return {"vm_name": vm_name, "error": str(e)}
    
    async def _fetch_vm_timestamps(self, vm_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Fetch instance view timestamps for a list of VMs.
        Returns a dict mapping resource_id -> days_inactive.
        """
        result = {}
        loop = asyncio.get_event_loop()
        
        # Process VMs in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(vm_list), batch_size):
            batch = vm_list[i:i + batch_size]
            logger.info(f"Enriching VMs batch {i//batch_size + 1}/{(len(vm_list) + batch_size - 1)//batch_size}...")
            
            tasks = []
            for vm in batch:
                resource_id = vm.get("resource_id", "")
                # Extract subscription, resource group, and VM name from resource ID
                # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{name}
                parts = resource_id.split("/")
                if len(parts) >= 9:
                    sub_id = parts[2]
                    rg = parts[4]
                    vm_name = parts[-1]
                    
                    task = loop.run_in_executor(
                        _executor,
                        self._get_vm_instance_view,
                        sub_id, rg, vm_name
                    )
                    tasks.append((resource_id, task))
            
            # Gather results for this batch
            for resource_id, task in tasks:
                try:
                    data = await task
                    if data.get("status_time"):
                        status_time = datetime.fromisoformat(data["status_time"].replace("Z", "+00:00"))
                        if status_time.tzinfo is None:
                            status_time = status_time.replace(tzinfo=timezone.utc)
                        days_inactive = (datetime.now(timezone.utc) - status_time).days
                        result[resource_id.lower()] = days_inactive
                except Exception as e:
                    logger.debug(f"Error enriching VM {resource_id}: {e}")
            
            # Small delay between batches
            await asyncio.sleep(0.2)
        
        return result
    
    async def enrich_scan_data(self, scan_id: str, data_dir: str):
        """
        Background task to enrich scan data with VM timestamps.
        Updates the orphaned.json file in place.
        """
        self._enrichment_status[scan_id] = "running"
        logger.info(f"Starting VM enrichment for scan {scan_id}...")
        
        try:
            orphaned_file = os.path.join(data_dir, "orphaned.json")
            
            if not os.path.exists(orphaned_file):
                logger.warning(f"Orphaned file not found: {orphaned_file}")
                self._enrichment_status[scan_id] = "failed"
                return
            
            # Load current data
            with open(orphaned_file, "r") as f:
                issues = json.load(f)
            
            # Find deallocated VMs that need enrichment
            vms_to_enrich = [
                issue for issue in issues
                if issue.get("issue_type") == "Deallocated VM" and issue.get("days_inactive") is None
            ]
            
            if not vms_to_enrich:
                logger.info("No VMs need enrichment")
                self._enrichment_status[scan_id] = "completed"
                return
            
            logger.info(f"Enriching {len(vms_to_enrich)} VMs...")
            
            # Fetch timestamps
            timestamps = await self._fetch_vm_timestamps(vms_to_enrich)
            
            # Update issues
            updated_count = 0
            for issue in issues:
                if issue.get("issue_type") == "Deallocated VM":
                    resource_id = issue.get("resource_id", "").lower()
                    if resource_id in timestamps:
                        issue["days_inactive"] = timestamps[resource_id]
                        # Update description to include days
                        if issue.get("description") and "days inactive" not in issue["description"]:
                            issue["description"] += f" - {timestamps[resource_id]} days inactive"
                        updated_count += 1
            
            # Save updated data
            with open(orphaned_file, "w") as f:
                json.dump(issues, f, indent=2, default=str)
            
            logger.info(f"VM enrichment complete: updated {updated_count} VMs")
            self._enrichment_status[scan_id] = "completed"
            
        except Exception as e:
            logger.error(f"VM enrichment failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._enrichment_status[scan_id] = "failed"
    
    def start_enrichment(self, scan_id: str, data_dir: str):
        """
        Start background enrichment task.
        This runs the enrichment in a separate task without blocking.
        """
        asyncio.create_task(self.enrich_scan_data(scan_id, data_dir))


vm_enrichment_service = VMEnrichmentService()
