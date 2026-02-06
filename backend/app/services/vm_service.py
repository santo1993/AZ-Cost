"""
VM Optimization Service.
"""
from typing import List
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..utils.logger import get_logger

logger = get_logger(__name__)

class VMService:
    async def analyze_vms(self, subscription_ids: List[str] = None) -> List[OptimizationIssue]:
        issues = []
        
        # Detect Stopped (but not Deallocated) VMs - you pay for compute!
        # PowerState/stopped means OS shut down but Azure resource still allocated
        query = """
        Resources
        | where type == "microsoft.compute/virtualmachines"
        | where properties.extended.instanceView.powerState.code == "PowerState/stopped"
        | project id, name, type, subscriptionId, resourceGroup, properties.hardwareProfile.vmSize
        """
        
        vms = await resource_graph_client.query_resources(query, subscriptions=subscription_ids)
        
        for vm in vms:
            issues.append(OptimizationIssue(
                id=f"vm-stopped-{vm['id']}",
                resource_id=vm['id'],
                resource_name=vm['name'],
                resource_type=vm['type'],
                subscription_id=vm['subscriptionId'],
                resource_group=vm['resourceGroup'],
                issue_type="VirtualMachine",
                severity="High",
                description="VM in 'Stopped' state (Billing continues)",
                potential_savings=0.0, # Depends on SKU
                recommendation="Deallocate the VM to stop billing."
            ))
            
        return issues

vm_service = VMService()
