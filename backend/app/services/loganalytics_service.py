"""
Log Analytics Service.
"""
from typing import List
from ..clients.resource_graph import resource_graph_client
from ..models.resource import OptimizationIssue
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class LogAnalyticsService:
    async def analyze_workspaces(self, subscription_ids: List[str] = None) -> List[OptimizationIssue]:
        settings = get_settings()
        issues = []
        
        # Query for workspaces with > 31 days retention (potential savings)
        # Note: retentionInDays might be in properties.features or properties directly depending on API version
        query = """
        Resources
        | where type == "microsoft.operationalinsights/workspaces"
        | project id, name, type, subscriptionId, resourceGroup, properties.retentionInDays, properties.sku.name
        """
        
        workspaces = await resource_graph_client.query_resources(query, subscriptions=subscription_ids)
        
        for ws in workspaces:
            retention = ws.get('properties', {}).get('retentionInDays', 30)
            sku = ws.get('properties', {}).get('sku', {}).get('name', 'Unknown')
            
            if retention > settings.log_analytics_retention_threshold:
                issues.append(OptimizationIssue(
                    id=f"log-analytics-retention-{ws['id']}",
                    resource_id=ws['id'],
                    resource_name=ws['name'],
                    resource_type=ws['type'],
                    subscription_id=ws['subscriptionId'],
                    resource_group=ws['resourceGroup'],
                    issue_type="LogAnalytics",
                    severity="Low",
                    description=f"High Retention ({retention} days)",
                    potential_savings=0.0, # Hard to estimate without ingestion volume
                    recommendation=f"Reduce retention to {settings.log_analytics_retention_threshold} days if audit requirements allow."
                ))
                
        return issues

log_analytics_service = LogAnalyticsService()
