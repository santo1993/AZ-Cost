
import asyncio
import logging
from app.services.orphaned_service import orphaned_service
from app.services.subscription_service import subscription_service

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger('azure').setLevel(logging.WARNING)

async def verify_fix():
    print("Fetching subscriptions...")
    subs = await subscription_service.get_subscriptions()
    print(f"Found {len(subs)} subscriptions")

    if not subs:
        print("No subscriptions found. Exiting.")
        return

    print("\n--- Testing Orphaned Service with zombie_days=0 ---")
    try:
        # Call the service with zombie_days=0 as we did in the fix, but disable costs for speed
        issues = await orphaned_service.detect_orphaned_resources(subs, zombie_days=0, include_costs=False)
        
        disks = [i for i in issues if i.resource_type == "Orphaned Disk"]
        snapshots = [i for i in issues if i.resource_type == "Old Snapshot"]
        
        print(f"Total Issues Found: {len(issues)}")
        print(f"Orphaned Disks Found: {len(disks)}")
        print(f"Snapshots Found: {len(snapshots)}")
        
        if len(disks) > 0:
            print("SUCCESS: Found orphaned disks with zombie_days=0")
        else:
            print("WARNING: No orphaned disks found (are there any?)")
            
    except Exception as e:
        print(f"Error calling orphaned_service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_fix())
