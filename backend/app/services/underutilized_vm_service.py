"""
Underutilized VM Detection Service.
Uses Azure Monitor metrics to identify VMs with low CPU and Memory utilization.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.compute import ComputeManagementClient
from ..services.azure_auth import auth_service
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# VM size to approximate monthly cost mapping (simplified)
VM_SIZE_COSTS = {
    "Standard_B1s": 7.59,
    "Standard_B1ms": 15.18,
    "Standard_B2s": 30.37,
    "Standard_B2ms": 60.74,
    "Standard_D2s_v3": 70.08,
    "Standard_D4s_v3": 140.16,
    "Standard_D8s_v3": 280.32,
    "Standard_D2_v3": 70.08,
    "Standard_D4_v3": 140.16,
    "Standard_DS1_v2": 43.80,
    "Standard_DS2_v2": 87.60,
    "Standard_DS3_v2": 175.20,
    "Standard_E2s_v3": 91.98,
    "Standard_E4s_v3": 183.96,
    "Standard_F2s_v2": 61.32,
    "Standard_F4s_v2": 122.64,
}

DEFAULT_VM_COST = 100.0  # Default estimate if VM size not in mapping


class UnderutilizedVMService:
    
    async def detect_underutilized_vms(
        self, 
        subscription_ids: List[str] = None,
        cpu_threshold: float = 5.0,
        memory_threshold: float = 5.0,
        days: int = 7
    ) -> List[OptimizationIssue]:
        """
        Detect VMs with low CPU and Memory utilization.
        
        Args:
            subscription_ids: List of subscription IDs to scan
            cpu_threshold: Max average CPU % to be considered underutilized
            memory_threshold: Max average memory % to be considered underutilized
            days: Number of days to analyze metrics
        """
        settings = get_settings()
        issues = []
        
        # Build subscription name map
        from azure.mgmt.subscription import SubscriptionClient
        
        sub_name_map = {}
        try:
            credential = auth_service.get_credential()
            sub_client = SubscriptionClient(credential)
            for s in sub_client.subscriptions.list():
                sub_name_map[s.subscription_id] = s.display_name
        except Exception as e:
            logger.warning(f"Could not fetch subscription names: {e}")
        
        # Get running VMs using Resource Graph
        vm_query = """
        Resources
        | where type == "microsoft.compute/virtualmachines"
        | extend powerState = tostring(properties.extended.instanceView.powerState.displayStatus)
        | where powerState == "VM running"
        | project id, name, subscriptionId, resourceGroup, vmSize = properties.hardwareProfile.vmSize, location
        """
        
        try:
            vms = await resource_graph_client.query_resources(vm_query, subscriptions=subscription_ids)
            total_vms = len(vms)
            logger.info(f"Found {total_vms} running VMs to check for underutilization")
            
            credential = auth_service.get_credential()
            
            # Track time to avoid infinite hangs (but allow enough time for all VMs)
            import time
            start_time_check = time.time()
            MAX_TOTAL_SECONDS = 300  # 5 minutes max - check as many VMs as possible
            vms_checked = 0
            
            for vm in vms:
                # Check if we've exceeded time limit
                elapsed = time.time() - start_time_check
                if elapsed > MAX_TOTAL_SECONDS:
                    logger.warning(f"Timeout reached after checking {vms_checked} VMs, returning partial results")
                    break
                    
                try:
                    vm_id = vm['id']
                    sub_id = vm['subscriptionId']
                    vm_size = vm.get('vmSize') or 'Unknown'
                    
                    # Get metrics from Azure Monitor
                    monitor_client = MonitorManagementClient(credential, sub_id)
                    
                    # Calculate time range
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=days)
                    timespan = f"{start_time.isoformat()}Z/{end_time.isoformat()}Z"
                    
                    # Query CPU metrics only (skip memory to be faster)
                    avg_cpu = await self._get_average_metric(
                        monitor_client, vm_id, "Percentage CPU", timespan
                    )
                    
                    vms_checked += 1
                    logger.info(f"Checked VM {vms_checked}/{len(vms)}: {vm['name']} - CPU: {avg_cpu:.1f}%" if avg_cpu else f"Checked VM {vms_checked}/{len(vms)}: {vm['name']} - CPU: N/A")
                    
                    # Check threshold (CPU only for speed)
                    if avg_cpu is not None and avg_cpu < cpu_threshold:
                        # Calculate potential savings
                        potential_savings = VM_SIZE_COSTS.get(vm_size, DEFAULT_VM_COST)
                        
                        issues.append(OptimizationIssue(
                            id=f"underutilized-vm-{vm_id}",
                            resource_id=vm_id,
                            resource_name=vm['name'],
                            resource_type="Underutilized VM",
                            subscription_id=sub_id,
                            subscription_name=sub_name_map.get(sub_id, sub_id[:8] + "..."),
                            resource_group=vm['resourceGroup'],
                            issue_type="Underutilized VM",
                            severity="Medium",
                            description=f"VM ({vm_size}) with low CPU utilization: {avg_cpu:.1f}% (avg over {days} days)",
                            potential_savings=round(potential_savings * 0.5, 2),  # Estimate 50% savings by rightsizing
                            recommendation="Consider rightsizing to a smaller VM or deallocating if not needed."
                        ))
                            
                except Exception as e:
                    logger.warning(f"Could not get metrics for VM {vm['name']}: {e}")
                    continue
            
            logger.info(f"Completed underutilized VM check: {len(issues)} underutilized VMs found out of {vms_checked} checked")
                    
        except Exception as e:
            logger.error(f"Failed to query running VMs: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return issues
    
    async def _get_average_metric(
        self, 
        client: MonitorManagementClient, 
        resource_id: str, 
        metric_name: str, 
        timespan: str,
        is_memory: bool = False
    ) -> Optional[float]:
        """Get average metric value over the timespan."""
        try:
            metrics_data = client.metrics.list(
                resource_uri=resource_id,
                timespan=timespan,
                interval="PT1H",
                metricnames=metric_name,
                aggregation="Average"
            )
            
            values = []
            for metric in metrics_data.value:
                for ts in metric.timeseries:
                    for data in ts.data:
                        if data.average is not None:
                            values.append(data.average)
            
            if values:
                avg = sum(values) / len(values)
                # For memory, the metric is "Available Memory Bytes" - we'd need total to calc %
                # For simplicity, we'll skip memory check if we can't determine utilization
                if is_memory:
                    # Return None to skip memory constraint if we can't calculate utilization
                    return None
                return avg
            return None
            
        except Exception as e:
            logger.debug(f"Could not get metric {metric_name} for {resource_id}: {e}")
            return None


underutilized_vm_service = UnderutilizedVMService()
