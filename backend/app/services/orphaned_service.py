"""
Orphaned/Zombie Resource Detection Service.
Includes actual cost data from Azure Cost Management.
Calculates VM costs including attached disk storage costs.
"""

from typing import List, Dict, Any
import asyncio
import datetime
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class OrphanedService:
    
    async def detect_orphaned_resources(self, subscription_ids: List[str] = None, include_costs: bool = True, zombie_days: int = 30) -> List[OptimizationIssue]:
        """
        Detect orphaned and zombie resources across subscriptions using bulk querying.
        """
        settings = get_settings()
        
        # Build subscription name map
        from azure.mgmt.subscription import SubscriptionClient
        from .azure_auth import auth_service
        
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

        # Chunk subscriptions
        chunk_size = 50
        chunks = [subs[i:i + chunk_size] for i in range(0, len(subs), chunk_size)]
        
        logger.info(f"Processing {len(subs)} subscriptions in {len(chunks)} chunks...")
        
        all_issues = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} subs)...")
            try:
                issues = await self._detect_for_chunk(chunk, sub_name_map, include_costs, zombie_days)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                
        return all_issues

    async def _detect_for_chunk(self, subs: List[str], sub_name_map: Dict[str, str], include_costs: bool, zombie_days: int) -> List[OptimizationIssue]:
        """
        Detect resources for a chunk of subscriptions using parallel queries.
        """
        issues = []
        
        # Get resource costs if requested
        cost_map = {}
        if include_costs:
            try:
                from .cost_service import cost_service
                cost_map = await cost_service.get_costs_by_resource(subs, days=30)
            except Exception as e:
                logger.warning(f"Failed to fetch resource costs for chunk: {e}")

        # Define Queries
        
        # 1. Disks
        disk_time_filter = f"| where todatetime(properties.timeCreated) < ago({zombie_days}d)" if zombie_days > 0 else ""
        disks_query = f"""
        Resources
        | where type == "microsoft.compute/disks"
        | where properties.diskState == "Unattached"
        {disk_time_filter}
        | project id, name, type, subscriptionId, resourceGroup, skuName = sku.name, diskSizeGB = properties.diskSizeGB, timeCreated = properties.timeCreated
        """
        
        # 2. PIPs
        pip_query = """
        Resources
        | where type == "microsoft.network/publicipaddresses"
        | where properties.ipConfiguration == ""
        | project id, name, type, subscriptionId, resourceGroup
        """
        
        # 3. All Disks (for VM cost calc)
        all_disks_query = """
        Resources
        | where type == "microsoft.compute/disks"
        | project id, name, diskSizeGB = properties.diskSizeGB, skuName = sku.name
        """
        
        # 4. VMs
        vm_query = """
        Resources
        | where type == "microsoft.compute/virtualmachines"
        | extend powerState = tostring(properties.extended.instanceView.powerState.displayStatus)
        | where powerState contains "deallocated" or powerState contains "stopped"
        | project id, name, type, subscriptionId, resourceGroup, 
                  vmSize = properties.hardwareProfile.vmSize,
                  osDiskId = properties.storageProfile.osDisk.managedDisk.id,
                  dataDisks = properties.storageProfile.dataDisks,
                  statuses = properties.extended.instanceView.statuses
        """
        
        # 5. Snapshots
        snap_time_filter = f"| where ageInDays > {zombie_days}" if zombie_days > 0 else ""
        snapshot_query = f"""
        Resources
        | where type == "microsoft.compute/snapshots"
        | extend ageInDays = datetime_diff('day', now(), todatetime(properties.timeCreated))
        {snap_time_filter}
        | project id, name, type, subscriptionId, resourceGroup, diskSizeGB = properties.diskSizeGB, ageInDays
        """
        
        # 6. Load Balancers
        lb_query = """
        Resources
        | where type == "microsoft.network/loadbalancers"
        | extend backendPoolCount = array_length(properties.backendAddressPools)
        | extend hasBackendConfigs = isnotnull(properties.backendAddressPools[0].properties.backendIPConfigurations)
        | where backendPoolCount == 0 or hasBackendConfigs == false
        | project id, name, subscriptionId, resourceGroup, skuName = sku.name, skuTier = sku.tier
        """
        
        # Execute queries in parallel
        try:
            results = await asyncio.gather(
                resource_graph_client.query_resources(disks_query, subscriptions=subs),
                resource_graph_client.query_resources(pip_query, subscriptions=subs),
                resource_graph_client.query_resources(all_disks_query, subscriptions=subs),
                resource_graph_client.query_resources(vm_query, subscriptions=subs),
                resource_graph_client.query_resources(snapshot_query, subscriptions=subs),
                resource_graph_client.query_resources(lb_query, subscriptions=subs),
                return_exceptions=True
            )
            
            disks_data, pips_data, all_disks_data, vms_data, snaps_data, lbs_data = results
            
            # Helper to check for exceptions
            def get_data(res, name):
                if isinstance(res, Exception):
                    logger.error(f"Error querying {name}: {res}")
                    return []
                return res

            disks = get_data(disks_data, "Disks")
            pips = get_data(pips_data, "PIPs")
            all_disks = get_data(all_disks_data, "All Disks")
            vms = get_data(vms_data, "VMs")
            snapshots = get_data(snaps_data, "Snapshots")
            load_balancers = get_data(lbs_data, "Load Balancers")

            # --- Process Disks ---
            for disk in disks:
                sub_id = disk.get('subscriptionId', '')
                sub_name = sub_name_map.get(sub_id, sub_id)
                size_gb = disk.get('diskSizeGB', 0) or 0
                resource_id = disk['id'].lower()
                actual_cost = cost_map.get(resource_id, 0.0)
                
                if actual_cost == 0 and size_gb > 0:
                    sku = disk.get('skuName', 'Standard_LRS')
                    if 'Premium' in str(sku): actual_cost = size_gb * 0.15
                    elif 'StandardSSD' in str(sku): actual_cost = size_gb * 0.08
                    else: actual_cost = size_gb * 0.04
                
                days_created = 0
                if disk.get('timeCreated'):
                    try:
                        created_time = datetime.datetime.fromisoformat(disk['timeCreated'].replace('Z', '+00:00'))
                        now_utc = datetime.datetime.now(datetime.timezone.utc)
                        if created_time.tzinfo is None:
                            created_time = created_time.replace(tzinfo=datetime.timezone.utc)
                        days_created = (now_utc - created_time).days
                    except:
                        pass

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
                    description=f"Unattached Managed Disk ({size_gb} GB) - created {days_created} days ago",
                    potential_savings=round(actual_cost, 2),
                    recommendation="Delete the unattached disk or attach it to a VM.",
                    days_inactive=days_created
                ))

            # --- Process PIPs ---
            for pip in pips:
                sub_id = pip.get('subscriptionId', '')
                sub_name = sub_name_map.get(sub_id, sub_id)
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

            # --- Process VMs ---
            # Create disk lookup map
            disk_info = {}
            for d in all_disks:
                disk_id = d['id'].lower()
                disk_info[disk_id] = {
                    'size_gb': d.get('diskSizeGB', 0) or 0,
                    'sku': d.get('skuName', 'Standard_LRS')
                }

            for vm in vms:
                sub_id = vm.get('subscriptionId', '')
                sub_name = sub_name_map.get(sub_id, sub_id)
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
                
                days_inactive = None
                statuses = vm.get('statuses', [])
                if statuses and isinstance(statuses, list):
                    for status in statuses:
                        code = status.get('code', '')
                        if 'PowerState/deallocated' in code or 'PowerState/stopped' in code:
                            time_str = status.get('time')
                            if time_str:
                                try:
                                    time_str = time_str.split('.')[0].replace('Z', '+00:00')
                                    deallocated_time = datetime.datetime.fromisoformat(time_str)
                                    if deallocated_time.tzinfo is None:
                                         deallocated_time = deallocated_time.replace(tzinfo=datetime.timezone.utc)
                                    days_inactive = (datetime.datetime.now(datetime.timezone.utc) - deallocated_time).days
                                except:
                                    pass
                                break

                desc = f"Deallocated VM ({vm_size}) with {disk_count} disk(s)"
                if days_inactive is not None:
                    desc += f" - {days_inactive} days inactive"

                issues.append(OptimizationIssue(
                    id=f"zombie-vm-{vm['id']}",
                    resource_id=vm['id'],
                    resource_name=vm['name'],
                    resource_type="Deallocated VM",
                    subscription_id=sub_id,
                    subscription_name=sub_name,
                    resource_group=vm['resourceGroup'],
                    issue_type="Deallocated VM",
                    severity="High" if (days_inactive and days_inactive > 30) else "Medium",
                    description=desc,
                    potential_savings=round(total_cost, 2),
                    recommendation="Delete or resize the VM if no longer needed. Consider snapshots for backup.",
                    days_inactive=days_inactive
                ))
            
            # --- Process Snapshots ---
            for snap in snapshots:
                sub_id = snap.get('subscriptionId', '')
                sub_name = sub_name_map.get(sub_id, sub_id)
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
                    recommendation="Delete old snapshots that are no longer needed.",
                    days_inactive=int(age_days)
                ))

            # --- Process LBs ---
            for lb in load_balancers:
                sub_id = lb.get('subscriptionId', '')
                sub_name = sub_name_map.get(sub_id, sub_id)
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
            logger.error(f"Error executing parallel queries for chunk: {e}")
            
        return issues

orphaned_service = OrphanedService()
