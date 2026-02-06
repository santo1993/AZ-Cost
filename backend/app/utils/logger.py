"""
Logging Utility.
"""

import logging
import sys
from ..config import get_settings

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a logger instance."""
    settings = get_settings()
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - correlation_id=%(correlation_id)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.setLevel(settings.log_level.upper())
    
    # Add a filter to ensure correlation_id is present if not provided
    class CorrelationFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'correlation_id'):
                record.correlation_id = '-'
            return True
            
    logger.addFilter(CorrelationFilter())
    
    return logger
