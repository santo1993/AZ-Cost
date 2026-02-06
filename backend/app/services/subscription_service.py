"""
Subscription Service.
"""
from typing import List
from azure.mgmt.subscription import SubscriptionClient
from .azure_auth import auth_service
from ..cache.memory_cache import memory_cache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SubscriptionService:
    async def get_subscriptions(self) -> List[str]:
        """
        Get list of all accessible subscription IDs.
        Cached for 1 hour.
        """
        return await memory_cache.get_or_set(
            "all_subscription_ids",
            self._fetch_subscriptions,
            force_refresh=False
        )
    
    async def _fetch_subscriptions(self) -> List[str]:
        """
        Fetch subscriptions from Azure.
        """
        logger.info("Fetching subscriptions from Azure...")
        try:
            credential = auth_service.get_credential()
            client = SubscriptionClient(credential)
            
            # SubscriptionClient is sync, but we wrap result in async structure if needed 
            # or just call it directly (blocking but fast)
            subs = list(client.subscriptions.list())
            ids = [s.subscription_id for s in subs]
            
            logger.info(f"Discovered {len(ids)} subscriptions.")
            return ids
        except Exception as e:
            logger.error(f"Failed to fetch subscriptions: {e}")
            return []

subscription_service = SubscriptionService()
