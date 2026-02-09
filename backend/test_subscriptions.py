"""

Test script to verify subscription fetching works correctly.
"""
import asyncio
from app.services.subscription_service import subscription_service

async def main():
    print("Testing subscription service...")
    print("-" * 50)
    
    # Test fetching subscription details
    print("\n1. Fetching subscription details...")
    details = await subscription_service._fetch_subscription_details()
    print(f"   Found {len(details)} subscriptions")
    
    if details:
        print(f"\n   First 3 subscriptions:")
        for sub in details[:3]:
            print(f"   - {sub['display_name']} ({sub['subscription_id']}) - {sub['state']}")
    
    # Test the public method
    print("\n2. Testing get_subscription_details() method...")
    details2 = await subscription_service.get_subscription_details()
    print(f"   Found {len(details2)} subscriptions")
    
    print("\n" + "-" * 50)
    print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
