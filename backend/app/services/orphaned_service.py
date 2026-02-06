"""
Orphaned/Zombie Resource Detection Service.
Includes actual cost data from Azure Cost Management.
Calculates VM costs including attached disk storage costs.
"""

from typing import List, Dict
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class OrphanedService:
    
    async def detect_orphaned_resources(self, subscription_ids: List[str] = None, include_costs: bool = True, zombie_days: int = 30) -> List[OptimizationIssue]:
        """
        Detect orphaned and zombie resources using Resource Graph.
        Includes actual cost data and attached resource costs.
        
        Args:
            subscription_ids: List of subscription IDs to scan
            include_costs: Whether to fetch actual costs from Cost Management
            zombie_days: Minimum days a resource must be inactive to be considered zombie
        """
        settings = get_settings()
        issues = []
        
        # Build subscription name map
        from azure.mgmt.subscription import SubscriptionClient
        from .azure_auth import auth_service
        
        sub_name_map = {}
        try:
            credential = auth_service.get_credential()
            sub_client = SubscriptionClient(credential)
            for s in sub_client.subscriptions.list():
                sub_name_map[s.subscription_id] = s.display_name
            logger.info(f"Fetched names for {len(sub_name_map)} subscriptions")
        except Exception as e:
            logger.warning(f"Could not fetch subscription names: {e}")
        
        # Get resource costs if requested
        cost_map = {}
        if include_costs:
            try:
                from .cost_service import cost_service
                cost_map = await cost_service.get_costs_by_resource(subscription_ids, days=30)
                logger.info(f"Fetched costs for {len(cost_map)} resources")
            except Exception as e:
                logger.error(f"Failed to fetch resource costs: {e}")
        
        # 1. Unattached Managed Disks
        disks_query = """
        Resources
        | where type == "microsoft.compute/disks"
        | where properties.diskState == "Unattached"
        | project id, name, type, subscriptionId, resourceGroup, skuName = sku.name, diskSizeGB = properties.diskSizeGB, timeCreated = properties.timeCreated
        """
        disks = await resource_graph_client.query_resources(disks_query, subscriptions=subscription_ids)
        for disk in disks:
            size_gb = disk.get('diskSizeGB', 0) or 0
            
            # Get actual cost from cost map
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
                subscription_id=disk['subscriptionId'],
                subscription_name=sub_name_map.get(disk['subscriptionId'], disk['subscriptionId'][:8] + "..."),
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
        pips = await resource_graph_client.query_resources(pip_query, subscriptions=subscription_ids)
        for pip in pips:
            resource_id = pip['id'].lower()
            actual_cost = cost_map.get(resource_id, 4.0)
            
            issues.append(OptimizationIssue(
                id=f"orphaned-pip-{pip['id']}",
                resource_id=pip['id'],
                resource_name=pip['name'],
                resource_type="Unattached Public IP",
                subscription_id=pip['subscriptionId'],
                subscription_name=sub_name_map.get(pip['subscriptionId'], pip['subscriptionId'][:8] + "..."),
                resource_group=pip['resourceGroup'],
                issue_type="Unattached Public IP",
                severity="Medium",
                description="Unattached Public IP Address",
                potential_savings=round(actual_cost, 2),
                recommendation="Delete the unattached Public IP."
            ))

        # 3. Deallocated VMs - Query all disks first to build a complete cost map
        # Get all managed disks and their costs
        all_disks_query = """
        Resources
        | where type == "microsoft.compute/disks"
        | project id, name, diskSizeGB = properties.diskSizeGB, skuName = sku.name
        """
        try:
            all_disks = await resource_graph_client.query_resources(all_disks_query, subscriptions=subscription_ids)
            disk_info = {}
            for d in all_disks:
                disk_id = d['id'].lower()
                disk_info[disk_id] = {
                    'size_gb': d.get('diskSizeGB', 0) or 0,
                    'sku': d.get('skuName', 'Standard_LRS')
                }
        except Exception as e:
            logger.warning(f"Could not query all disks: {e}")
            disk_info = {}
        
        # Query VMs with their disk IDs
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
        try:
            vms = await resource_graph_client.query_resources(vm_query, subscriptions=subscription_ids)
            logger.info(f"Found {len(vms)} deallocated VMs")
            
            for vm in vms:
                resource_id = vm['id'].lower()
                vm_size = vm.get('vmSize') or 'Unknown'
                
                # Get OS disk cost - try multiple ways to get disk ID
                os_disk_id = vm.get('osDiskId', '')
                if os_disk_id:
                    os_disk_id = os_disk_id.lower()
                
                # Calculate OS disk cost
                os_disk_cost = cost_map.get(os_disk_id, 0.0)
                if os_disk_cost == 0 and os_disk_id in disk_info:
                    info = disk_info[os_disk_id]
                    size_gb = info['size_gb']
                    sku = info['sku']
                    if 'Premium' in str(sku):
                        os_disk_cost = size_gb * 0.15
                    elif 'StandardSSD' in str(sku):
                        os_disk_cost = size_gb * 0.08
                    else:
                        os_disk_cost = size_gb * 0.04
                
                # Get data disk costs
                data_disk_cost = 0.0
                disk_count = 1  # OS disk
                data_disks = vm.get('dataDisks', [])
                if isinstance(data_disks, list):
                    disk_count += len(data_disks)
                    for dd in data_disks:
                        if isinstance(dd, dict):
                            managed_disk = dd.get('managedDisk', {})
                            if isinstance(managed_disk, dict):
                                dd_id = managed_disk.get('id', '').lower()
                            else:
                                dd_id = ''
                            
                            dd_cost = cost_map.get(dd_id, 0.0)
                            if dd_cost == 0 and dd_id in disk_info:
                                info = disk_info[dd_id]
                                size_gb = info['size_gb']
                                sku = info['sku']
                                if 'Premium' in str(sku):
                                    dd_cost = size_gb * 0.15
                                elif 'StandardSSD' in str(sku):
                                    dd_cost = size_gb * 0.08
                                else:
                                    dd_cost = size_gb * 0.04
                            data_disk_cost += dd_cost
                
                # Total storage cost (VM compute is already stopped, so no compute cost)
                total_cost = os_disk_cost + data_disk_cost
                
                logger.info(f"VM {vm['name']}: OS disk cost=${os_disk_cost:.2f}, Data disk cost=${data_disk_cost:.2f}, Total=${total_cost:.2f}")
                
                issues.append(OptimizationIssue(
                    id=f"zombie-vm-{vm['id']}",
                    resource_id=vm['id'],
                    resource_name=vm['name'],
                    resource_type="Deallocated VM",
                    subscription_id=vm['subscriptionId'],
                    subscription_name=sub_name_map.get(vm['subscriptionId'], vm['subscriptionId'][:8] + "..."),
                    resource_group=vm['resourceGroup'],
                    issue_type="Deallocated VM",
                    severity="High",
                    description=f"Deallocated VM ({vm_size}) with {disk_count} disk(s) - storage costs continue",
                    potential_savings=round(total_cost, 2),
                    recommendation="Delete or resize the VM if no longer needed. Consider snapshots for backup."
                ))
        except Exception as e:
            logger.warning(f"Could not query deallocated VMs: {e}")
            import traceback
            logger.warning(traceback.format_exc())

        # 4. Old Snapshots (> configurable days)
        snapshot_query = f"""
        Resources
        | where type == "microsoft.compute/snapshots"
        | extend ageInDays = datetime_diff('day', now(), todatetime(properties.timeCreated))
        | where ageInDays > {zombie_days}
        | project id, name, type, subscriptionId, resourceGroup, diskSizeGB = properties.diskSizeGB, ageInDays
        """
        try:
            snapshots = await resource_graph_client.query_resources(snapshot_query, subscriptions=subscription_ids)
            for snap in snapshots:
                resource_id = snap['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                size_gb = snap.get('diskSizeGB') or 0
                age_days = snap.get('ageInDays') or zombie_days
                
                if actual_cost == 0 and size_gb:
                    actual_cost = float(size_gb) * 0.05  # ~$0.05/GB/month for snapshots
                
                issues.append(OptimizationIssue(
                    id=f"old-snapshot-{snap['id']}",
                    resource_id=snap['id'],
                    resource_name=snap['name'],
                    resource_type="Old Snapshot",
                    subscription_id=snap['subscriptionId'],
                    subscription_name=sub_name_map.get(snap['subscriptionId'], snap['subscriptionId'][:8] + "..."),
                    resource_group=snap['resourceGroup'],
                    issue_type="Old Snapshot",
                    severity="Medium",
                    description=f"Old Snapshot ({size_gb} GB) - {int(age_days)} days old",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete old snapshots that are no longer needed."
                ))
        except Exception as e:
            logger.warning(f"Could not query old snapshots: {e}")
        
        # 5. Idle Load Balancers (no backend targets)
        lb_query = """
        Resources
        | where type == "microsoft.network/loadbalancers"
        | extend backendPoolCount = array_length(properties.backendAddressPools)
        | extend hasBackendConfigs = isnotnull(properties.backendAddressPools[0].properties.backendIPConfigurations)
        | where backendPoolCount == 0 or hasBackendConfigs == false
        | project id, name, subscriptionId, resourceGroup, skuName = sku.name, skuTier = sku.tier
        """
        try:
            load_balancers = await resource_graph_client.query_resources(lb_query, subscriptions=subscription_ids)
            logger.info(f"Found {len(load_balancers)} idle load balancers")
            
            for lb in load_balancers:
                resource_id = lb['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                sku_name = lb.get('skuName') or 'Basic'  # Handle None value
                
                # Estimate cost if not in cost map (~$18/month for Standard, free for Basic)
                if actual_cost == 0:
                    if sku_name == 'Standard':
                        actual_cost = 18.0  # Standard LB fixed cost per month
                    else:
                        actual_cost = 0.0  # Basic LB is free
                
                issues.append(OptimizationIssue(
                    id=f"idle-lb-{lb['id']}",
                    resource_id=lb['id'],
                    resource_name=lb['name'],
                    resource_type="Idle Load Balancer",
                    subscription_id=lb['subscriptionId'],
                    subscription_name=sub_name_map.get(lb['subscriptionId'], lb['subscriptionId'][:8] + "..."),
                    resource_group=lb['resourceGroup'],
                    issue_type="Idle Load Balancer",
                    severity="Medium",
                    description=f"Load Balancer ({sku_name}) with no backend targets",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete the idle load balancer or configure backend pools."
                ))
        except Exception as e:
            logger.warning(f"Could not query idle load balancers: {e}")
        
        return issues

orphaned_service = OrphanedService()
