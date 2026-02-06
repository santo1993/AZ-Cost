"""
Orphaned/Zombie Resource Detection Service.
Includes actual cost data from Azure Cost Management.
Calculates VM costs including attached disk storage costs.
"""

from typing import List, Dict
import asyncio
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class OrphanedService:
    
    async def detect_orphaned_resources(self, subscription_ids: List[str] = None, include_costs: bool = True, zombie_days: int = 30) -> List[OptimizationIssue]:
        """
        Detect orphaned and zombie resources across subscriptions using batch processing.
        """
        settings = get_settings()
        
        # Build subscription name map
        from azure.mgmt.subscription import SubscriptionClient
        from .azure_auth import auth_service
        from ..utils.batch import batch_process
        
        subs = subscription_ids
        if not subs:
            from .subscription_service import subscription_service
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            logger.warning("No subscriptions found for orphaned resource check")
            return []

        sub_name_map = {}
        try:
            credential = auth_service.get_credential()
            sub_client = SubscriptionClient(credential)
            for s in sub_client.subscriptions.list():
                sub_name_map[s.subscription_id] = s.display_name
            logger.info(f"Fetched names for {len(sub_name_map)} subscriptions")
        except Exception as e:
            logger.warning(f"Could not fetch subscription names: {e}")

        # Helper function for batch processing
        async def process_sub(sub_id: str):
             return await self._detect_for_subscription(sub_id, sub_name_map.get(sub_id, sub_id[:8]), include_costs, zombie_days)

        logger.info(f"Scanning for orphaned resources in {len(subs)} subscriptions (batch processing)...")
        results_nested = await batch_process(
            subs,
            process_sub,
            batch_size=5,
            delay_seconds=0.1 # Fast batching
        )
        
        # Flatten results
        all_issues = [issue for sub_results in results_nested for issue in sub_results]
        return all_issues

    async def _detect_for_subscription(self, sub_id: str, sub_name: str, include_costs: bool, zombie_days: int) -> List[OptimizationIssue]:
        """
        Detect resources for a single subscription.
        """
        issues = []
        try:
            # Get resource costs if requested (per subscription now)
            cost_map = {}
            if include_costs:
                try:
                    from .cost_service import cost_service
                    # We use get_costs_by_resource but ideally we should have a scoped cached version? 
                    # Assuming cost_service handles caching correctly.
                    # Note: calling this 75 times might flood if not careful, but cost_service uses cache
                    cost_map = await cost_service.get_costs_by_resource([sub_id], days=30)
                except Exception as e:
                    logger.warning(f"Failed to fetch resource costs for {sub_id}: {e}")

            # 1. Unattached Managed Disks
            disks_query = """
            Resources
            | where type == "microsoft.compute/disks"
            | where properties.diskState == "Unattached"
            | project id, name, type, subscriptionId, resourceGroup, skuName = sku.name, diskSizeGB = properties.diskSizeGB, timeCreated = properties.timeCreated
            """
            disks = await resource_graph_client.query_resources(disks_query, subscriptions=[sub_id])
            for disk in disks:
                size_gb = disk.get('diskSizeGB', 0) or 0
                resource_id = disk['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                
                # If no actual cost, estimate based on size and SKU
                if actual_cost == 0 and size_gb > 0:
                    sku = disk.get('skuName', 'Standard_LRS')
                    if 'Premium' in str(sku):
                        actual_cost = size_gb * 0.15
                    elif 'StandardSSD' in str(sku):
                        actual_cost = size_gb * 0.08
                    else:
                        actual_cost = size_gb * 0.04
                
                issues.append(OptimizationIssue(
                    id=f"orphaned-disk-{disk['id']}",
                    resource_id=disk['id'],
                    resource_name=disk['name'],
                    resource_type="Orphaned Disk",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=disk['resourceGroup'],
                    issue_type="Orphaned Disk",
                    severity="High",
                    description=f"Unattached Managed Disk ({size_gb} GB)",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete the unattached disk or attach it to a VM."
                ))

            # 2. Unattached Public IPs
            pip_query = """
            Resources
            | where type == "microsoft.network/publicipaddresses"
            | where properties.ipConfiguration == ""
            | project id, name, type, subscriptionId, resourceGroup
            """
            pips = await resource_graph_client.query_resources(pip_query, subscriptions=[sub_id])
            for pip in pips:
                resource_id = pip['id'].lower()
                actual_cost = cost_map.get(resource_id, 4.0)
                
                issues.append(OptimizationIssue(
                    id=f"orphaned-pip-{pip['id']}",
                    resource_id=pip['id'],
                    resource_name=pip['name'],
                    resource_type="Unattached Public IP",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=pip['resourceGroup'],
                    issue_type="Unattached Public IP",
                    severity="Medium",
                    description="Unattached Public IP Address",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete the unattached Public IP."
                ))

            # 3. Deallocated VMs
            all_disks_query = """
            Resources
            | where type == "microsoft.compute/disks"
            | project id, name, diskSizeGB = properties.diskSizeGB, skuName = sku.name
            """
            try:
                all_disks = await resource_graph_client.query_resources(all_disks_query, subscriptions=[sub_id])
                disk_info = {}
                for d in all_disks:
                    disk_id = d['id'].lower()
                    disk_info[disk_id] = {
                        'size_gb': d.get('diskSizeGB', 0) or 0,
                        'sku': d.get('skuName', 'Standard_LRS')
                    }
            except Exception:
                disk_info = {}
            
            vm_query = """
            Resources
            | where type == "microsoft.compute/virtualmachines"
            | extend powerState = tostring(properties.extended.instanceView.powerState.displayStatus)
            | where powerState contains "deallocated" or powerState contains "stopped"
            | project id, name, type, subscriptionId, resourceGroup, 
                      vmSize = properties.hardwareProfile.vmSize,
                      osDiskId = properties.storageProfile.osDisk.managedDisk.id,
                      dataDisks = properties.storageProfile.dataDisks
            """
            vms = await resource_graph_client.query_resources(vm_query, subscriptions=[sub_id])
            
            for vm in vms:
                resource_id = vm['id'].lower()
                vm_size = vm.get('vmSize') or 'Unknown'
                
                os_disk_id = vm.get('osDiskId', '')
                if os_disk_id: os_disk_id = os_disk_id.lower()
                
                os_disk_cost = cost_map.get(os_disk_id, 0.0)
                if os_disk_cost == 0 and os_disk_id in disk_info:
                    info = disk_info[os_disk_id]
                    size_gb = info['size_gb']
                    sku = info['sku']
                    if 'Premium' in str(sku): os_disk_cost = size_gb * 0.15
                    elif 'StandardSSD' in str(sku): os_disk_cost = size_gb * 0.08
                    else: os_disk_cost = size_gb * 0.04
                
                data_disk_cost = 0.0
                disk_count = 1
                data_disks = vm.get('dataDisks', [])
                if isinstance(data_disks, list):
                    disk_count += len(data_disks)
                    for dd in data_disks:
                        if isinstance(dd, dict):
                            managed_disk = dd.get('managedDisk', {})
                            if isinstance(managed_disk, dict):
                                dd_id = managed_disk.get('id', '').lower()
                                dd_cost = cost_map.get(dd_id, 0.0)
                                if dd_cost == 0 and dd_id in disk_info:
                                    info = disk_info[dd_id]
                                    size_gb = info['size_gb']
                                    sku = info['sku']
                                    if 'Premium' in str(sku): dd_cost = size_gb * 0.15
                                    elif 'StandardSSD' in str(sku): dd_cost = size_gb * 0.08
                                    else: dd_cost = size_gb * 0.04
                                data_disk_cost += dd_cost

                total_cost = os_disk_cost + data_disk_cost
                
                issues.append(OptimizationIssue(
                    id=f"zombie-vm-{vm['id']}",
                    resource_id=vm['id'],
                    resource_name=vm['name'],
                    resource_type="Deallocated VM",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=vm['resourceGroup'],
                    issue_type="Deallocated VM",
                    severity="High",
                    description=f"Deallocated VM ({vm_size}) with {disk_count} disk(s) - storage costs continue",
                    potential_savings=round(total_cost, 2),
                    recommendation="Delete or resize the VM if no longer needed. Consider snapshots for backup."
                ))

            # 4. Old Snapshots
            snapshot_query = f"""
            Resources
            | where type == "microsoft.compute/snapshots"
            | extend ageInDays = datetime_diff('day', now(), todatetime(properties.timeCreated))
            | where ageInDays > {zombie_days}
            | project id, name, type, subscriptionId, resourceGroup, diskSizeGB = properties.diskSizeGB, ageInDays
            """
            snapshots = await resource_graph_client.query_resources(snapshot_query, subscriptions=[sub_id])
            for snap in snapshots:
                resource_id = snap['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                size_gb = snap.get('diskSizeGB') or 0
                age_days = snap.get('ageInDays') or zombie_days
                
                if actual_cost == 0 and size_gb:
                    actual_cost = float(size_gb) * 0.05
                
                issues.append(OptimizationIssue(
                    id=f"old-snapshot-{snap['id']}",
                    resource_id=snap['id'],
                    resource_name=snap['name'],
                    resource_type="Old Snapshot",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=snap['resourceGroup'],
                    issue_type="Old Snapshot",
                    severity="Medium",
                    description=f"Old Snapshot ({size_gb} GB) - {int(age_days)} days old",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete old snapshots that are no longer needed."
                ))

            # 5. Idle Load Balancers
            lb_query = """
            Resources
            | where type == "microsoft.network/loadbalancers"
            | extend backendPoolCount = array_length(properties.backendAddressPools)
            | extend hasBackendConfigs = isnotnull(properties.backendAddressPools[0].properties.backendIPConfigurations)
            | where backendPoolCount == 0 or hasBackendConfigs == false
            | project id, name, subscriptionId, resourceGroup, skuName = sku.name, skuTier = sku.tier
            """
            load_balancers = await resource_graph_client.query_resources(lb_query, subscriptions=[sub_id])
            for lb in load_balancers:
                resource_id = lb['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                sku_name = lb.get('skuName') or 'Basic'
                
                if actual_cost == 0:
                    if sku_name == 'Standard': actual_cost = 18.0
                    else: actual_cost = 0.0
                
                issues.append(OptimizationIssue(
                    id=f"idle-lb-{lb['id']}",
                    resource_id=lb['id'],
                    resource_name=lb['name'],
                    resource_type="Idle Load Balancer",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=lb['resourceGroup'],
                    issue_type="Idle Load Balancer",
                    severity="Medium",
                    description=f"Load Balancer ({sku_name}) with no backend targets",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete the idle load balancer or configure backend pools."
                ))
                
        except Exception as e:
            logger.error(f"Error processing subscription {sub_id} for orphans: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return issues

orphaned_service = OrphanedService()
