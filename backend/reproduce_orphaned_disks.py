
import asyncio
import logging
from app.clients.resource_graph import resource_graph_client
from app.services.subscription_service import subscription_service

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger('azure').setLevel(logging.WARNING)

async def test_orphaned_resources():
    print("Fetching subscriptions...")
    subs = await subscription_service.get_subscriptions()
    print(f"Found {len(subs)} subscriptions")

    if not subs:
        print("No subscriptions found. Exiting.")
        return

    with open("reproduce_orphaned_disks.txt", "w") as f:
        # 1. Test Disks Query
        f.write("\n--- Testing Disks Query ---\n")
        disks_query = """
        Resources
        | where type == "microsoft.compute/disks"
        | where properties.diskState == "Unattached"
        | project id, name, type, subscriptionId, resourceGroup, skuName = sku.name, diskSizeGB = properties.diskSizeGB, timeCreated = properties.timeCreated
        """
        
        try:
            disks = await resource_graph_client.query_resources(disks_query, subscriptions=subs)
            f.write(f"Found {len(disks)} orphaned disks\n")
            if disks:
                f.write(f"Sample disk: {disks[0]}\n")
        except Exception as e:
            f.write(f"Error querying disks: {e}\n")

        # 2. Test Snapshots Query
        f.write("\n--- Testing Snapshots Query ---\n")
        snapshot_query = """
        Resources
        | where type == "microsoft.compute/snapshots"
        | extend ageInDays = datetime_diff('day', now(), todatetime(properties.timeCreated))
        | project id, name, type, subscriptionId, resourceGroup, diskSizeGB = properties.diskSizeGB, ageInDays, timeCreated = properties.timeCreated
        """
        
        try:
            snapshots = await resource_graph_client.query_resources(snapshot_query, subscriptions=subs)
            f.write(f"Found {len(snapshots)} snapshots\n")
            if snapshots:
                f.write(f"Sample snapshot: {snapshots[0]}\n")
        except Exception as e:
            f.write(f"Error querying snapshots: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_orphaned_resources())
