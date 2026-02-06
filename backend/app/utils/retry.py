"""
Retry Utility.

Provides decorators for exponential backoff and retry logic.
"""

import asyncio
import functools
import random
from typing import Type, Tuple, Optional, Callable
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from .logger import get_logger

logger = get_logger(__name__)

def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (HttpResponseError, ServiceRequestError)
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Handlers:
    - HTTP 429: Respects Retry-After header
    - Network/Service errors: Exponential backoff with jitter
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            current_delay = base_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    # Handle Rate Limiting (429)
                    retry_after = None
                    if isinstance(e, HttpResponseError) and e.status_code == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                retry_seconds = float(retry_after)
                                logger.warning(f"Rate limited (429). Retrying after {retry_seconds}s...")
                                await asyncio.sleep(retry_seconds)
                                continue
                            except ValueError:
                                pass # Fallback to exponential backoff
                    
                    # Exponential Backoff with Jitter
                    sleep_time = min(current_delay * (2 ** (retries - 1)), max_delay)
                    jitter = random.uniform(0, 0.1 * sleep_time)
                    total_sleep = sleep_time + jitter
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} due to {type(e).__name__}. "
                        f"Sleeping {total_sleep:.2f}s..."
                    )
                    
                    await asyncio.sleep(total_sleep)
                    
        return wrapper
    return decorator
