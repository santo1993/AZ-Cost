"""
Scan Service for managing data persistence.
Saves and loads scan results from disk.
"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ScanService:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = os.path.abspath(data_dir)
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")
            
    def _get_scan_path(self, scan_id: str) -> str:
        return os.path.join(self.data_dir, scan_id)
    
    def get_scan_dir(self, scan_id: str) -> str:
        """Get the directory path for a scan (public method for enrichment service)."""
        return self._get_scan_path(scan_id)
        
    def create_scan_id(self) -> str:
        """Generate a unique scan ID based on timestamp."""
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
    def save_scan(self, scan_id: str, data: Dict[str, Any]) -> bool:
        """
        Save scan data to disk.
        Structure:
        data/
          <scan_id>/
            summary.json
            costs.json
            orphaned.json
            ...
        """
        try:
            scan_path = self._get_scan_path(scan_id)
            if not os.path.exists(scan_path):
                os.makedirs(scan_path)
                
            # Metadata
            metadata = {
                "scan_id": scan_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed",
                "total_subscriptions": data.get("total_subscriptions", 0),
                "total_cost": data.get("total_costs", {}).get("total", 0),
                "total_potential_savings": data.get("savings_summary", {}).get("total_potential_monthly_savings", 0)
            }
            
            with open(os.path.join(scan_path, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)
                
            # Save individual components to separate files
            if "costs" in data:
                with open(os.path.join(scan_path, "costs.json"), "w") as f:
                    json.dump(data["costs"], f, indent=2)
            
            if "orphaned" in data:
                with open(os.path.join(scan_path, "orphaned.json"), "w") as f:
                    issues = [issue.dict() for issue in data["orphaned"]] if data["orphaned"] else []
                    json.dump(issues, f, indent=2)
                    
            if "advisor" in data:
                with open(os.path.join(scan_path, "advisor.json"), "w") as f:
                    issues = [issue.dict() for issue in data["advisor"]] if data["advisor"] else []
                    json.dump(issues, f, indent=2)
            
            if "savings_summary" in data:
                with open(os.path.join(scan_path, "savings_summary.json"), "w") as f:
                    json.dump(data["savings_summary"], f, indent=2)

            logger.info(f"Successfully saved scan {scan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save scan {scan_id}: {e}")
            return False

    def list_scans(self) -> List[Dict[str, Any]]:
        """List all available scans with metadata."""
        scans = []
        if not os.path.exists(self.data_dir):
            return []
            
        for item in os.listdir(self.data_dir):
            scan_path = os.path.join(self.data_dir, item)
            if os.path.isdir(scan_path):
                metadata_file = os.path.join(scan_path, "metadata.json")
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            scans.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for scan {item}: {e}")
                        
        # Sort by timestamp descending (newest first)
        scans.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return scans
        
    def load_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Load specific scan data."""
        scan_path = self._get_scan_path(scan_id)
        if not os.path.exists(scan_path):
            return None
            
        data = {}
        try:
            # Load components
            if os.path.exists(os.path.join(scan_path, "costs.json")):
                with open(os.path.join(scan_path, "costs.json"), "r") as f:
                    data["costs"] = json.load(f)
                    
            if os.path.exists(os.path.join(scan_path, "orphaned.json")):
                with open(os.path.join(scan_path, "orphaned.json"), "r") as f:
                    data["orphaned"] = json.load(f)
                    
            if os.path.exists(os.path.join(scan_path, "advisor.json")):
                with open(os.path.join(scan_path, "advisor.json"), "r") as f:
                    data["advisor"] = json.load(f)

            if os.path.exists(os.path.join(scan_path, "savings_summary.json")):
                with open(os.path.join(scan_path, "savings_summary.json"), "r") as f:
                    data["savings_summary"] = json.load(f)
                    
            return data
            
        except Exception as e:
            logger.error(f"Failed to load scan {scan_id}: {e}")
            return None

# Singleton instance
scan_service = ScanService()
