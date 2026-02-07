"""
Cost Export Service.
Handles downloading and parsing of Azure Cost Export CSVs from Blob Storage.
"""

import os
import io
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from azure.storage.blob import ContainerClient
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CostExportService:
    def __init__(self):
        self.settings = get_settings()
        self._blob_service_client = None
        self._container_client = None

    def _get_container_client(self) -> Optional[ContainerClient]:
        """Get container client - recreated each time to pick up config changes."""
        settings = get_settings()
        
        if not settings.azure_storage_account_url or not settings.azure_storage_sas_token:
            logger.warning("Azure Storage credentials not configured")
            return None
            
        try:
            account_url = settings.azure_storage_account_url
            sas_token = settings.azure_storage_sas_token.strip()
            container_name = settings.azure_storage_container
            
            full_url = f"{account_url}/{container_name}?{sas_token}"
            logger.info(f"Connecting to blob storage: {account_url}/{container_name}")
            
            return ContainerClient.from_container_url(full_url)
        except Exception as e:
            logger.error(f"Failed to create Blob Container Client: {e}")
            return None

    def list_exports(self) -> List[Dict[str, Any]]:
        """List available export files in the configured path."""
        client = self._get_container_client()
        if not client:
            return []
            
        prefix = self.settings.azure_cost_export_path or ""
        exports = []
        
        try:
            blobs = client.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                if blob.name.endswith('.csv'):
                    exports.append({
                        "name": blob.name,
                        "last_modified": blob.last_modified.isoformat(),
                        "size": blob.size,
                        "url": client.get_blob_client(blob).url # Note: URL might need SAS to be accessible
                    })
            
            # Sort by last modified descending
            exports.sort(key=lambda x: x['last_modified'], reverse=True)
            return exports
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            return []

    def get_latest_data(self, progress_callback=None) -> Dict[str, Any]:
        """
        Download and parse the latest export CSV.
        Returns aggregated cost data suitable for the dashboard.
        Blocking method - should be run in a separate thread.
        """
        exports = self.list_exports()
        if not exports:
            raise FileNotFoundError("No export CSVs found in the configured path")
            
        latest_blob_name = exports[0]["name"]
        logger.info(f"Processing latest export: {latest_blob_name}")
        
        return self.process_export_blob(latest_blob_name, progress_callback)

    def process_export_blob(self, blob_name: str, progress_callback=None) -> Dict[str, Any]:
        """
        Download blob to temp file and parse with Pandas.
        Aggregates data by Subscription, ResourceGroup, Service, and Date.
        """
        client = self._get_container_client()
        if not client:
             raise ValueError("Storage client not initialized")
             
        temp_file = "temp_cost_export.csv"
        try:
            # 1. Download with Progress
            logger.info(f"Downloading {blob_name}...")
            blob_client = client.get_blob_client(blob_name)
            props = blob_client.get_blob_properties()
            total_size = props.size
            
            with open(temp_file, "wb") as file:
                download_stream = blob_client.download_blob()
                downloaded = 0
                
                # Chunk size 4MB
                for chunk in download_stream.chunks():
                    file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        # Report download progress (0-50%)
                        percent = int((downloaded / total_size) * 50)
                        progress_callback(percent, f"Downloading CSV... ({downloaded/1024/1024:.0f}MB / {total_size/1024/1024:.0f}MB)")

            logger.info("Download complete. Parsed CSV...")
            if progress_callback:
                progress_callback(55, "Parsing CSV (this may take a moment)...")

            # 2. Parse with Pandas
            # Use chunks for parsing if file is huge? For now read_csv is usually optimized enough.
            # If 1.3GB CSV, it might be 3-4GB RAM.
            df = pd.read_csv(temp_file)
            
            # Normalize Columns (Azure Exports change over time)
            col_map = {
                'SubscriptionId': 'subscription_id',
                'SubscriptionGuid': 'subscription_id',  # Alternative column name
                'SubscriptionName': 'subscription_name',
                'ResourceGroup': 'resource_group',
                'ServiceName': 'service_name',
                'MeterCategory': 'service_name',  # Alternative for service
                'PreTaxCost': 'cost',
                'CostInBillingCurrency': 'cost',
                'UsageDateTime': 'date',
                'Date': 'date'
            }
            
            # Rename columns that exist in the map
            df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
            
            # Ensure required columns exist
            required = ['subscription_id', 'cost', 'date']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"CSV missing required columns: {missing}. Found: {df.columns.tolist()}")

            # Convert date
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Fill NaN
            df['cost'] = df['cost'].fillna(0.0)
            df['service_name'] = df.get('service_name', 'Unknown')
            df['resource_group'] = df.get('resource_group', 'Unknown')
            
            if progress_callback:
                progress_callback(80, "Aggregating Data...")

            # Aggregations
            
            # 1. Total Sub Costs
            sub_costs = df.groupby(['subscription_id', 'subscription_name'])['cost'].sum().reset_index()
            subscriptions_data = []
            for _, row in sub_costs.iterrows():
                subscriptions_data.append({
                    "subscription_id": row['subscription_id'],
                    "display_name": row['subscription_name'] if pd.notna(row['subscription_name']) else row['subscription_id'],
                    "cost": float(row['cost']),
                    "currency": "USD" 
                })
                
            # 2. Daily History (Global)
            daily_costs = df.groupby('date')['cost'].sum().reset_index()
            history = {str(row['date']): float(row['cost']) for _, row in daily_costs.iterrows()}
            
            # 3. Service Breakdown
            service_costs = df.groupby('service_name')['cost'].sum().sort_values(ascending=False).head(10).reset_index()
            services = {row['service_name']: float(row['cost']) for _, row in service_costs.iterrows()}
            
            result = {
                "total_cost": float(df['cost'].sum()),
                "currency": "USD", 
                "subscriptions": subscriptions_data,
                "history": history,
                "services": services,
                "raw_record_count": len(df),
                "data_source": "Azure Cost Export",
                "export_file": blob_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Export processing complete. Total Cost: ${result['total_cost']:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error processing export blob: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

cost_export_service = CostExportService()
