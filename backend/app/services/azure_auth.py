"""
Azure Authentication Service.

Handles credential creation based on configuration.
"""

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.credentials import TokenCredential
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AzureAuthService:
    _credential: TokenCredential | None = None

    @classmethod
    def get_credential(cls) -> TokenCredential:
        """
        Get the Azure TokenCredential based on configuration.
        Singleton pattern to avoid recreating credentials.
        """
        if cls._credential:
            return cls._credential

        settings = get_settings()
        
        try:
            if settings.azure_auth_mode.upper() == "SERVICE_PRINCIPAL":
                if not all([settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret]):
                    raise ValueError("Missing required environment variables for SERVICE_PRINCIPAL auth.")
                
                logger.info("Initializing Service Principal credentials")
                cls._credential = ClientSecretCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret
                )
            else:
                logger.info("Initializing DefaultAzureCredential (CLI/Environment)")
                # DefaultAzureCredential tries environment vars, managed identity, CLI, etc.
                cls._credential = DefaultAzureCredential()
            
            return cls._credential
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure credentials: {e}")
            raise

auth_service = AzureAuthService
