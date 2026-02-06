"""
Savings Summary Service.
"""

from typing import Dict, Any, List
from .orphaned_service import orphaned_service
from .advisor_service import advisor_service
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SavingsService:
    
    async def get_savings_summary(self, subscription_ids: List[str] = None) -> Dict[str, Any]:
        """
        Aggregate all savings opportunities.
        """
        # Fetch in parallel in real implementation; sequential for now
        logger.info("Calculating savings summary...")
        
        orphaned = await orphaned_service.detect_orphaned_resources(subscription_ids)
        advisor = await advisor_service.get_recommendations(subscription_ids)
        
        all_issues = orphaned + advisor
        
        total_savings = sum(i.potential_savings for i in all_issues)
        by_category = {}
        
        for issue in all_issues:
            cat = issue.issue_type
            by_category[cat] = by_category.get(cat, 0) + issue.potential_savings
            
        return {
            "total_potential_monthly_savings": total_savings,
            "savings_by_category": by_category,
            "total_recommendations": len(all_issues),
            "breakdown": [i.model_dump() for i in all_issues]
        }

savings_service = SavingsService()
