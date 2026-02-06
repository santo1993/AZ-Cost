"""
Subscription Service.
"""
from typing import List
from azure.mgmt.subscription import SubscriptionClient
from .azure_auth import auth_service
from ..cache.memory_cache import memory_cache
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SubscriptionService:
    async def get_subscriptions(self) -> List[str]:
        """
        Get list of subscription IDs.
        Uses configured subscriptions from .env first, falls back to auto-discovery.
        Cached for 1 hour.
        """
        # First check if subscriptions are configured in .env
        settings = get_settings()
        configured_subs = settings.subscription_ids_list
        
        if configured_subs:
            logger.info(f"Using {len(configured_subs)} configured subscription(s) from .env")
            return configured_subs
        
        # Fall back to auto-discovery only if no subscriptions configured
        logger.info("No subscriptions configured, auto-discovering from tenant...")
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
    
    async def get_subscription_details(self) -> list:
        """
        Get subscription details with names and IDs.
        """
        return await memory_cache.get_or_set(
            "subscription_details",
            self._fetch_subscription_details,
            force_refresh=False
        )
    
    async def _fetch_subscription_details(self) -> list:
        """
        Fetch subscription details from Azure.
        """
        logger.info("Fetching subscription details from Azure...")
        try:
            credential = auth_service.get_credential()
            client = SubscriptionClient(credential)
            
            subs = list(client.subscriptions.list())
            details = []
            for s in subs:
                details.append({
                    "subscription_id": s.subscription_id,
                    "display_name": s.display_name,
                    "state": s.state.value if s.state else "Unknown"
                })
            
            logger.info(f"Fetched details for {len(details)} subscriptions.")
            return details
        except Exception as e:
            logger.error(f"Failed to fetch subscription details: {e}")
            return []

subscription_service = SubscriptionService()
