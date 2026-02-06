"""
Resource Discovery Service.
"""

from typing import List, Optional
from ..clients.resource_graph import resource_graph_client
from ..models.resource import Resource
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ResourceDiscoveryService:
    
    async def get_all_resources(
        self,
        subscription_ids: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Resource]:
        """
        Fetch resources using Resource Graph.
        """
        settings = get_settings()
        subs = subscription_ids or settings.subscription_ids_list
        
        # Base Query
        query = """
        Resources
        | project 
            id, 
            name, 
            type, 
            subscriptionId, 
            resourceGroup, 
            location, 
            tags, 
            sku, 
            kind, 
            managedBy, 
            properties
        """
        
        if resource_types:
            types_str = "', '".join(resource_types)
            query += f"| where type in ('{types_str}')"
            
        if limit and limit > 0:
            query += f"| limit {limit}"
            
        results = await resource_graph_client.query_resources(query, subscriptions=subs)
        
        # Map to Pydantic models
        resources = []
        for item in results:
            try:
                resources.append(Resource(
                    id=item.get('id'),
                    name=item.get('name'),
                    type=item.get('type'),
                    subscription_id=item.get('subscriptionId'),
                    resource_group=item.get('resourceGroup'),
                    location=item.get('location'),
                    tags=item.get('tags') or {},
                    sku=item.get('sku'),
                    kind=item.get('kind'),
                    managed_by=item.get('managedBy'),
                    properties=item.get('properties') or {}
                ))
            except Exception as e:
                logger.warning(f"Failed to parse resource {item.get('id')}: {e}")
                
        return resources

resource_discovery_service = ResourceDiscoveryService()
