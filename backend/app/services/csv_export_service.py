"""
CSV Export Service.
"""
import csv
import io
from typing import List, AsyncGenerator
from ..services.resource_discovery import resource_discovery_service
from ..models.resource import Resource
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CSVExportService:
    
    async def generate_resource_csv_stream(
        self, 
        subscription_ids: List[str] = None,
        resource_types: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates a CSV stream of resources.
        """
        logger.info("Starting CSV export stream...")
        
        # Header
        header = ["SubscriptionID", "ResourceGroup", "Name", "Type", "Location", "Tags"]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        # Fetch all resources (this might need to be paginated internally for TRUE streaming)
        # resource_discovery_service.get_all_resources currently fetches ALL.
        # Ideally, we'd make get_all_resources yield pages too.
        # For now, we fetch all (up to default limits) and stream the CSV writing.
        
        resources = await resource_discovery_service.get_all_resources(
            subscription_ids=subscription_ids, 
            resource_types=resource_types,
            limit=5000 # Higher limit for export
        )
        
        for res in resources:
            tags_str = "; ".join([f"{k}={v}" for k, v in res.tags.items()])
            writer.writerow([
                res.subscription_id,
                res.resource_group,
                res.name,
                res.type,
                res.location,
                tags_str
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
        logger.info(f"Exported {len(resources)} resources to CSV stream.")

csv_export_service = CSVExportService()
