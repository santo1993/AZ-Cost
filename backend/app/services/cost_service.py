"""
Azure Cost Management Service.

Fetches actual cost data from Azure Cost Management API.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryDefinition, 
    QueryTimePeriod, 
    QueryDataset, 
    QueryAggregation,
    QueryGrouping,
    ExportType,
    TimeframeType
)
from ..services.azure_auth import auth_service
from ..services.subscription_service import subscription_service
from ..cache.memory_cache import memory_cache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CostService:
    
    async def get_subscription_costs(self, subscription_ids: List[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get total costs by subscription for the specified time period.
        """
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            logger.warning("No subscriptions available for cost query.")
            return {"subscriptions": [], "total": 0.0}
        
        credential = auth_service.get_credential()
        
        # Calculate date range (last N days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        results = []
        total_cost = 0.0
        
        for sub_id in subs:
            try:
                client = CostManagementClient(credential)
                scope = f"/subscriptions/{sub_id}"
                
                # Define query for aggregated cost
                query = QueryDefinition(
                    type=ExportType.ACTUAL_COST,
                    timeframe=TimeframeType.CUSTOM,
                    time_period=QueryTimePeriod(
                        from_property=start_date,
                        to=end_date
                    ),
                    dataset=QueryDataset(
                        granularity="None",
                        aggregation={
                            "totalCost": QueryAggregation(
                                name="Cost",
                                function="Sum"
                            )
                        }
                    )
                )
                
                response = client.query.usage(scope=scope, parameters=query)
                
                # Parse response
                cost = 0.0
                if response.rows and len(response.rows) > 0:
                    # First column is typically the cost value
                    cost = float(response.rows[0][0]) if response.rows[0][0] else 0.0
                
                results.append({
                    "subscription_id": sub_id,
                    "cost": round(cost, 2),
                    "currency": "USD",  # Default, may need to parse from response
                    "period_days": days
                })
                total_cost += cost
                
            except Exception as e:
                logger.error(f"Failed to fetch costs for subscription {sub_id}: {e}")
                results.append({
                    "subscription_id": sub_id,
                    "cost": 0.0,
                    "currency": "USD",
                    "error": str(e)
                })
        
        return {
            "subscriptions": results,
            "total": round(total_cost, 2),
            "currency": "USD",
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    
    async def get_costs_by_resource_group(self, subscription_ids: List[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get costs grouped by resource group.
        """
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            return []
        
        credential = auth_service.get_credential()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        all_results = []
        
        for sub_id in subs:
            try:
                client = CostManagementClient(credential)
                scope = f"/subscriptions/{sub_id}"
                
                query = QueryDefinition(
                    type=ExportType.ACTUAL_COST,
                    timeframe=TimeframeType.CUSTOM,
                    time_period=QueryTimePeriod(
                        from_property=start_date,
                        to=end_date
                    ),
                    dataset=QueryDataset(
                        granularity="None",
                        aggregation={
                            "totalCost": QueryAggregation(
                                name="Cost",
                                function="Sum"
                            )
                        },
                        grouping=[
                            QueryGrouping(
                                type="Dimension",
                                name="ResourceGroup"
                            )
                        ]
                    )
                )
                
                response = client.query.usage(scope=scope, parameters=query)
                
                if response.rows:
                    for row in response.rows:
                        # row format: [cost, resource_group_name, ...]
                        cost = float(row[0]) if row[0] else 0.0
                        rg_name = row[1] if len(row) > 1 else "Unknown"
                        
                        all_results.append({
                            "subscription_id": sub_id,
                            "resource_group": rg_name,
                            "cost": round(cost, 2),
                            "currency": "USD"
                        })
                        
            except Exception as e:
                logger.error(f"Failed to fetch costs by RG for subscription {sub_id}: {e}")
        
        # Sort by cost descending
        all_results.sort(key=lambda x: x["cost"], reverse=True)
        return all_results

    async def get_monthly_cost_history(self, subscription_ids: List[str] = None, months: int = 12) -> Dict[str, Any]:
        """
        Get monthly cost history with breakdown by service type (resource type).
        Returns data suitable for a stacked bar chart.
        """
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            return {"months": [], "services": [], "data": []}
        
        credential = auth_service.get_credential()
        
        # Calculate date range (last N months)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        all_data = []
        all_services = set()
        
        for sub_id in subs:
            try:
                client = CostManagementClient(credential)
                scope = f"/subscriptions/{sub_id}"
                
                query = QueryDefinition(
                    type=ExportType.ACTUAL_COST,
                    timeframe=TimeframeType.CUSTOM,
                    time_period=QueryTimePeriod(
                        from_property=start_date,
                        to=end_date
                    ),
                    dataset=QueryDataset(
                        granularity="Monthly",
                        aggregation={
                            "totalCost": QueryAggregation(
                                name="Cost",
                                function="Sum"
                            )
                        },
                        grouping=[
                            QueryGrouping(
                                type="Dimension",
                                name="ServiceName"
                            )
                        ]
                    )
                )
                
                response = client.query.usage(scope=scope, parameters=query)
                
                if response.rows:
                    for row in response.rows:
                        # row format: [cost, date, service_name, currency]
                        cost = float(row[0]) if row[0] else 0.0
                        # Date is typically in YYYYMMDD format or ISO format
                        date_val = str(row[1]) if len(row) > 1 else ""
                        service_name = row[2] if len(row) > 2 else "Other"
                        
                        # Parse month from date
                        try:
                            if len(date_val) == 8:  # YYYYMMDD
                                month_str = f"{date_val[:4]}-{date_val[4:6]}"
                            else:
                                month_str = date_val[:7]  # YYYY-MM
                        except:
                            month_str = "Unknown"
                        
                        all_services.add(service_name)
                        all_data.append({
                            "month": month_str,
                            "service": service_name,
                            "cost": round(cost, 2),
                            "subscription_id": sub_id
                        })
                        
            except Exception as e:
                logger.error(f"Failed to fetch monthly costs for subscription {sub_id}: {e}")
        
        # Aggregate by month and service
        aggregated = {}
        for item in all_data:
            key = (item["month"], item["service"])
            if key not in aggregated:
                aggregated[key] = 0.0
            aggregated[key] += item["cost"]
        
        # Convert to list format for charting
        chart_data = []
        for (month, service), cost in aggregated.items():
            chart_data.append({
                "month": month,
                "service": service,
                "cost": round(cost, 2)
            })
        
        # Sort by month
        chart_data.sort(key=lambda x: x["month"])
        
        # Get unique months
        unique_months = sorted(list(set(d["month"] for d in chart_data)))
        
        return {
            "months": unique_months,
            "services": sorted(list(all_services)),
            "data": chart_data,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

cost_service = CostService()
