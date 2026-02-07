"""
Azure Resource Graph Client.
"""

from azure.mgmt.resourcegraph import ResourceGraphClient as AzureResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions
from ..services.azure_auth import auth_service
from ..utils.retry import retry_with_backoff
from ..utils.logger import get_logger
from typing import List, Dict, Any

logger = get_logger(__name__)

class ResourceGraphClient:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> AzureResourceGraphClient:
        if not self._client:
            self._client = AzureResourceGraphClient(auth_service.get_credential())
        return self._client

    @retry_with_backoff()
    async def query_resources(self, query: str, subscriptions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Execute a KQL query against Azure Resource Graph.
        Handles pagination automatically.
        """
        # Resolve subscriptions if not provided
        if not subscriptions:
            from ..services.subscription_service import subscription_service
            subscriptions = await subscription_service.get_subscriptions()
            
        if not subscriptions:
            logger.warning("No subscriptions available for ARG query.")
            return []

        all_results = []
        skip_token = None
        
        while True:
            # Use proper QueryRequestOptions object (result_format defaults to objectArray)
            options = QueryRequestOptions(
                skip_token=skip_token
            )
            
            request = QueryRequest(
                query=query,
                subscriptions=subscriptions,
                options=options
            )
            
            logger.debug(f"Executing ARG Query: {query[:100]}...")
            import asyncio
            response = await asyncio.to_thread(self.client.resources, request)
            
            if response.data:
                all_results.extend(response.data)
                
            # Handle pagination
            if not response.skip_token:
                break
                
            skip_token = response.skip_token
            
        return all_results

resource_graph_client = ResourceGraphClient()
