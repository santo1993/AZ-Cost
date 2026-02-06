"""
Azure Advisor Service.
"""

from typing import List, Dict, Any
from azure.mgmt.advisor import AdvisorManagementClient
from ..services.azure_auth import auth_service
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AdvisorService:
    
    async def get_recommendations(self, subscription_ids: List[str] = None) -> List[OptimizationIssue]:
        """
        Fetch Azure Advisor recommendations.
        Note: Advisor API is per-subscription.
        """
        settings = get_settings()
        subs = subscription_ids or settings.subscription_ids_list
        
        if not subs:
            from .subscription_service import subscription_service
            subs = await subscription_service.get_subscriptions()
            
        issues = []
        
        credential = auth_service.get_credential()
        
        if not subs:
            logger.warning("No subscription IDs found for Advisor check.")
            return []

        for sub_id in subs:
            try:
                client = AdvisorManagementClient(credential, sub_id)
                # Filter for Cost recommendations (Category = Cost)
                recs = client.recommendations.list(filter="Category eq 'Cost'")
                
                for rec in recs:
                    # Parse extended properties for savings
                    # Advisor savings logic can be complex
                    savings = 0.0
                    props = rec.extended_properties or {}
                    if 'savingsAmount' in props:
                        try:
                            savings = float(props['savingsAmount'])
                        except:
                            pass
                            
                    issues.append(OptimizationIssue(
                        id=f"advisor-{rec.name}",
                        resource_id=rec.resource_metadata.resource_id,
                        resource_name=rec.resource_metadata.resource_id.split('/')[-1] if rec.resource_metadata.resource_id else "Unknown",
                        resource_type=rec.impacted_field, # Rough mapping
                        subscription_id=sub_id,
                        resource_group="Multiple" if not rec.resource_metadata.resource_id else rec.resource_metadata.resource_id.split('/resourceGroups/')[1].split('/')[0],
                        issue_type="Advisor",
                        severity=rec.impact or "Medium",
                        description=rec.short_description.problem if rec.short_description else "Advisor Recommendation",
                        potential_savings=savings,
                        recommendation=rec.short_description.solution if rec.short_description else "Follow Advisor guide."
                    ))

            except Exception as e:
                logger.error(f"Failed to fetch Advisor recommendations for subscription {sub_id}: {e}")
                
        return issues

advisor_service = AdvisorService()
