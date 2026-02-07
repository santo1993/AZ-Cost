"""
Azure Cost Dashboard - Backend Configuration

Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure Authentication
    azure_auth_mode: str = Field(
        default="CLI",
        description="Authentication mode: 'CLI' or 'SERVICE_PRINCIPAL'"
    )
    azure_tenant_id: Optional[str] = Field(
        default=None,
        description="Azure Tenant ID (required for SERVICE_PRINCIPAL mode)"
    )
    azure_client_id: Optional[str] = Field(
        default=None,
        description="Azure Client ID (required for SERVICE_PRINCIPAL mode)"
    )
    azure_client_secret: Optional[str] = Field(
        default=None,
        description="Azure Client Secret (required for SERVICE_PRINCIPAL mode)"
    )
    
    # Subscriptions
    azure_subscription_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated subscription IDs (empty for auto-discover)"
    )
    
    # Cache Settings
    cache_ttl_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Cache TTL in hours (1-24)"
    )

    # Azure Cost Export (Storage)
    azure_storage_account_url: Optional[str] = Field(default=None)
    azure_storage_container: Optional[str] = Field(default=None)
    azure_storage_sas_token: Optional[str] = Field(default=None)
    azure_cost_export_path: Optional[str] = Field(default=None)
    
    # Server Settings
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    
    # CORS Settings
    frontend_url: str = Field(
        default="http://localhost:8501",
        description="Frontend URL for CORS"
    )
    
    # Detection Thresholds
    zombie_days_threshold: int = Field(
        default=90,
        description="Days of inactivity to consider a VM as zombie"
    )
    snapshot_age_days: int = Field(
        default=365,
        description="Days after which a snapshot is considered old"
    )
    log_analytics_retention_threshold: int = Field(
        default=31,
        description="Retention days threshold for Log Analytics"
    )
    
    @property
    def subscription_ids_list(self) -> List[str]:
        """Parse comma-separated subscription IDs into a list."""
        if not self.azure_subscription_ids:
            return []
        return [s.strip() for s in self.azure_subscription_ids.split(",") if s.strip()]
    
    @property
    def cache_ttl_seconds(self) -> int:
        """Convert cache TTL to seconds."""
        return self.cache_ttl_hours * 3600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

def clear_settings_cache():
    """Clear the settings cache to reload from .env."""
    get_settings.cache_clear()

# Clear cache on module import to ensure fresh settings when uvicorn reloads
clear_settings_cache()
