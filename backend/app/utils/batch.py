"""
Batch processing utilities.
"""
import asyncio
from typing import TypeVar, List, Callable, Any, Awaitable

T = TypeVar("T")
R = TypeVar("R")

async def batch_process(
    items: List[T],
    processor: Callable[[T], Awaitable[R]],
    batch_size: int = 5,
    delay_seconds: float = 1.0
) -> List[R]:
    """
    Process items in batches with delay between batches.
    
    Args:
        items: List of items to process
        processor: Async function to process each item
        batch_size: Number of items per batch
        delay_seconds: Delay in seconds between batches
        
    Returns:
        List of results
    """
    results = []
    total = len(items)
    
    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        
        # Process batch concurrently
        batch_results = await asyncio.gather(*[processor(item) for item in batch])
        results.extend(batch_results)
        
        # Delay if this isn't the last batch
        if i + batch_size < total:
            await asyncio.sleep(delay_seconds)
            
    return results
