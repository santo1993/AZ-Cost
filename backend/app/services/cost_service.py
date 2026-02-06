"""
Azure Cost Management Service.

Fetches actual cost data from Azure Cost Management API.
Uses concurrent execution for faster multi-subscription queries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
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

# Thread pool for concurrent Azure SDK calls (they are sync)
_executor = ThreadPoolExecutor(max_workers=5)

class CostService:
    
    def _query_subscription_cost(self, sub_id: str, start_date: datetime, end_date: datetime, days: int) -> Dict[str, Any]:
        """Sync method to query cost for a single subscription."""
        logger.info(f"Querying cost for subscription {sub_id} ({start_date.date()} to {end_date.date()})")
        try:
            credential = auth_service.get_credential()
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
                    granularity="Daily",  # "None" often fails, use Daily and sum
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum"
                        )
                    }
                )
            )
            
            response = client.query.usage(scope=scope, parameters=query)
            
            cost = 0.0
            if response.rows:
                # Sum up cost from all daily rows
                for row in response.rows:
                     if row[0]:
                         cost += float(row[0])
            
            # FALLBACK: If ActualCost is 0, try AmortizedCost
            if cost == 0.0:
                 logger.info(f"Subscription {sub_id}: ActualCost is 0, trying AmortizedCost...")
                 query.type = ExportType.AMORTIZED_COST
                 response = client.query.usage(scope=scope, parameters=query)
                 if response.rows:
                    for row in response.rows:
                        if row[0]:
                            cost += float(row[0])
                 logger.info(f"Subscription {sub_id}: AmortizedCost = ${cost:.2f}")
            else:
                logger.info(f"Subscription {sub_id}: Total Cost = ${cost:.2f}")
            
            return {
                "subscription_id": sub_id,
                "cost": round(cost, 2),
                "currency": "USD", # Defaulting to USD, should ideally take from response
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch costs for subscription {sub_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "subscription_id": sub_id,
                "cost": 0.0,
                "currency": "USD",
                "error": str(e)
            }
    
    async def get_subscription_costs(self, subscription_ids: List[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get total costs by subscription for the specified time period (parallel execution)."""
        from azure.mgmt.subscription import SubscriptionClient
        
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            logger.warning("No subscriptions available for cost query.")
            return {"subscriptions": [], "total": 0.0}
        
        # Build subscription name map (fast, sync call)
        sub_name_map = {}
        try:
            credential = auth_service.get_credential()
            sub_client = SubscriptionClient(credential)
            for s in sub_client.subscriptions.list():
                sub_name_map[s.subscription_id] = s.display_name
        except Exception as e:
            logger.warning(f"Could not fetch subscription names: {e}")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Run queries in parallel using thread pool
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._query_subscription_cost, sub_id, start_date, end_date, days)
            for sub_id in subs
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Add subscription names to results
        for r in results:
            sub_id = r.get("subscription_id", "")
            r["subscription_name"] = sub_name_map.get(sub_id, sub_id[:8] + "...")
        
        total_cost = sum(r["cost"] for r in results)
        
        return {
            "subscriptions": results,
            "total": round(total_cost, 2),
            "currency": "USD",
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    
    def _query_costs_by_rg(self, sub_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Sync method to query costs by resource group for a single subscription."""
        try:
            credential = auth_service.get_credential()
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
                    granularity="Daily", # Changed from None to Daily
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
            
            # Aggregate daily results by RG
            rg_costs = {}
            if response.rows:
                for row in response.rows:
                    cost = float(row[0]) if row[0] else 0.0
                    # With Daily granularity, row structure might trigger date column?
                    # Usually [Cost, Date, ResourceGroup] or [Cost, ResourceGroup, Date] ?
                    # Let's check grouping order or assume last cols are dimensions
                    # Typically: [Cost, Date, Grouping1, Grouping2...]
                    # row[0] = Cost
                    # row[1] = UsageDate (because Daily)
                    # row[2] = ResourceGroup
                    
                    rg_name = "Unknown"
                    if len(row) > 2:
                        rg_name = row[2]
                        
                    if rg_name not in rg_costs:
                        rg_costs[rg_name] = 0.0
                    rg_costs[rg_name] += cost

            results = []
            for rg_name, cost in rg_costs.items():
                results.append({
                    "subscription_id": sub_id,
                    "resource_group": rg_name,
                    "cost": round(cost, 2),
                    "currency": "USD"
                })
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch costs by RG for subscription {sub_id}: {e}")
            return []
    
    async def get_costs_by_resource_group(self, subscription_ids: List[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get costs grouped by resource group (parallel execution)."""
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            return []
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._query_costs_by_rg, sub_id, start_date, end_date)
            for sub_id in subs
        ]
        
        results_nested = await asyncio.gather(*tasks)
        all_results = [item for sublist in results_nested for item in sublist]
        
        all_results.sort(key=lambda x: x["cost"], reverse=True)
        return all_results

    def _query_monthly_history(self, sub_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Sync method to query monthly history for a single subscription."""
        try:
            credential = auth_service.get_credential()
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
            
            results = []
            if response.rows:
                for row in response.rows:
                    cost = float(row[0]) if row[0] else 0.0
                    date_val = str(row[1]) if len(row) > 1 else ""
                    service_name = row[2] if len(row) > 2 else "Other"
                    
                    try:
                        if len(date_val) == 8:
                            month_str = f"{date_val[:4]}-{date_val[4:6]}"
                        else:
                            month_str = date_val[:7]
                    except:
                        month_str = "Unknown"
                    
                    results.append({
                        "month": month_str,
                        "service": service_name,
                        "cost": round(cost, 2),
                        "subscription_id": sub_id
                    })
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch monthly costs for subscription {sub_id}: {e}")
            return []

    async def get_monthly_cost_history(self, subscription_ids: List[str] = None, months: int = 12) -> Dict[str, Any]:
        """Get monthly cost history with breakdown by service type (parallel execution)."""
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            return {"months": [], "services": [], "data": []}
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._query_monthly_history, sub_id, start_date, end_date)
            for sub_id in subs
        ]
        
        results_nested = await asyncio.gather(*tasks)
        all_data = [item for sublist in results_nested for item in sublist]
        
        # Collect all services
        all_services = set(item["service"] for item in all_data)
        
        # Aggregate by month and service
        aggregated = {}
        for item in all_data:
            key = (item["month"], item["service"])
            if key not in aggregated:
                aggregated[key] = 0.0
            aggregated[key] += item["cost"]
        
        chart_data = [
            {"month": month, "service": service, "cost": round(cost, 2)}
            for (month, service), cost in aggregated.items()
        ]
        
        chart_data.sort(key=lambda x: x["month"])
        unique_months = sorted(list(set(d["month"] for d in chart_data)))
        
        return {
            "months": unique_months,
            "services": sorted(list(all_services)),
            "data": chart_data,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    def _query_costs_by_resource(self, sub_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Sync method to query costs by individual resource for a subscription."""
        try:
            credential = auth_service.get_credential()
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
                            name="ResourceId"
                        )
                    ]
                )
            )
            
            response = client.query.usage(scope=scope, parameters=query)
            
            results = []
            if response.rows:
                for row in response.rows:
                    cost = float(row[0]) if row[0] else 0.0
                    resource_id = row[1] if len(row) > 1 else ""
                    
                    # Extract resource name from resource ID
                    resource_name = resource_id.split("/")[-1] if resource_id else "Unknown"
                    
                    results.append({
                        "resource_id": resource_id.lower(),
                        "resource_name": resource_name,
                        "cost": round(cost, 2),
                        "subscription_id": sub_id
                    })
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch costs by resource for subscription {sub_id}: {e}")
            return []

    async def get_costs_by_resource(self, subscription_ids: List[str] = None, days: int = 30) -> Dict[str, float]:
        """
        Get costs by individual resource ID (parallel execution).
        Returns a dict mapping resource_id (lowercase) -> cost.
        """
        subs = subscription_ids
        if not subs:
            subs = await subscription_service.get_subscriptions()
            
        if not subs:
            return {}
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._query_costs_by_resource, sub_id, start_date, end_date)
            for sub_id in subs
        ]
        
        results_nested = await asyncio.gather(*tasks)
        
        # Build a dict of resource_id -> cost
        cost_map = {}
        for sublist in results_nested:
            for item in sublist:
                resource_id = item["resource_id"]
                if resource_id:
                    cost_map[resource_id] = item["cost"]
        
        return cost_map

cost_service = CostService()
