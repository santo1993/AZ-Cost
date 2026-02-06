"""
Storage Optimization Service.
"""
from typing import List
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..utils.logger import get_logger

logger = get_logger(__name__)

class StorageService:
    async def analyze_storage(self, subscription_ids: List[str] = None) -> List[OptimizationIssue]:
        issues = []
        
        # Legacy v1 accounts
        query = """
        Resources
        | where type == "microsoft.storage/storageaccounts"
        | where kind == "Storage" or kind == "BlobStorage" 
        | where kind != "StorageV2" and kind != "FileStorage" and kind != "BlockBlobStorage"
        | project id, name, type, subscriptionId, resourceGroup, kind
        """
        
        accounts = await resource_graph_client.query_resources(query, subscriptions=subscription_ids)
        
        for acc in accounts:
            issues.append(OptimizationIssue(
                id=f"storage-legacy-{acc['id']}",
                resource_id=acc['id'],
                resource_name=acc['name'],
                resource_type=acc['type'],
                subscription_id=acc['subscriptionId'],
                resource_group=acc['resourceGroup'],
                issue_type="Storage",
                severity="Low",
                description=f"Legacy Storage Account ({acc.get('kind')})",
                potential_savings=0.0,
                recommendation="Upgrade to StorageV2 for better performance and features."
            ))
            
        return issues

storage_service = StorageService()
