"""
Seed subscription plans into database.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from botspool_shared_utils.database.connection import DatabaseManager
from botspool_shared_utils.database.models import SubscriptionPlanModel
from botspool_shared_utils.models.enums import SubscriptionTier
from uuid import uuid4


SUBSCRIPTION_PLANS = [
    {
        "tier": SubscriptionTier.FREE,
        "name": "Free Plan",
        "description": "Get started with basic AI assistance",
        "price_monthly": 0,  # cents
        "price_yearly": 0,
        "currency": "USD",
        "limits": {
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "requests_per_day": 500,
            "max_graphs": ["todo"],
            "storage_gb": 1
        },
        "features": {
            "todo_graph": True,
            "email_graph": False,
            "calendar_graph": False,
            "priority_support": False,
            "advanced_analytics": False
        },
        "billing_cycle": "monthly",
        "trial_days": 0,
        "is_active": True,
        "is_popular": False
    },
    {
        "tier": SubscriptionTier.BASIC,
        "name": "Basic Plan",
        "description": "Essential AI tools for productivity",
        "price_monthly": 990,  # $9.90
        "price_yearly": 9900,  # $99.00
        "currency": "USD",
        "limits": {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 5000,
            "max_graphs": ["todo", "email"],
            "storage_gb": 10
        },
        "features": {
            "todo_graph": True,
            "email_graph": True,
            "calendar_graph": False,
            "priority_support": False,
            "advanced_analytics": False
        },
        "billing_cycle": "monthly",
        "trial_days": 7,
        "is_active": True,
        "is_popular": True
    },
    {
        "tier": SubscriptionTier.PREMIUM,
        "name": "Premium Plan",
        "description": "Advanced AI capabilities for power users",
        "price_monthly": 2990,  # $29.90
        "price_yearly": 29900,  # $299.00
        "currency": "USD",
        "limits": {
            "requests_per_minute": 120,
            "requests_per_hour": 5000,
            "requests_per_day": 20000,
            "max_graphs": ["todo", "email", "calendar", "custom"],
            "storage_gb": 50
        },
        "features": {
            "todo_graph": True,
            "email_graph": True,
            "calendar_graph": True,
            "custom_graphs": True,
            "priority_support": True,
            "advanced_analytics": True
        },
        "billing_cycle": "monthly",
        "trial_days": 14,
        "is_active": True,
        "is_popular": False
    },
    {
        "tier": SubscriptionTier.ENTERPRISE,
        "name": "Enterprise Plan",
        "description": "Enterprise-grade AI platform",
        "price_monthly": 9990,  # $99.90
        "price_yearly": 99900,  # $999.00
        "currency": "USD",
        "limits": {
            "requests_per_minute": 300,
            "requests_per_hour": 10000,
            "requests_per_day": 100000,
            "max_graphs": ["all"],
            "storage_gb": 500
        },
        "features": {
            "todo_graph": True,
            "email_graph": True,
            "calendar_graph": True,
            "custom_graphs": True,
            "unlimited_graphs": True,
            "priority_support": True,
            "dedicated_support": True,
            "advanced_analytics": True,
            "custom_integrations": True,
            "sla_guarantee": True
        },
        "billing_cycle": "monthly",
        "trial_days": 30,
        "is_active": True,
        "is_popular": False
    }
]


async def seed_subscription_plans():
    """Seed subscription plans."""
    database_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/botspool_gateway"
    
    db_manager = DatabaseManager(database_url=database_url)
    await db_manager.initialize()
    
    try:
        async with db_manager.get_session_context() as session:
            for plan_data in SUBSCRIPTION_PLANS:
                # Check if plan already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(SubscriptionPlanModel).where(
                        SubscriptionPlanModel.tier == plan_data["tier"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"Plan {plan_data['tier'].value} already exists, skipping...")
                    continue
                
                # Create plan
                plan = SubscriptionPlanModel(
                    id=uuid4(),
                    tier=plan_data["tier"],
                    name=plan_data["name"],
                    description=plan_data["description"],
                    price_monthly=plan_data["price_monthly"],
                    price_yearly=plan_data["price_yearly"],
                    currency=plan_data["currency"],
                    limits=plan_data["limits"],
                    features=plan_data["features"],
                    billing_cycle=plan_data["billing_cycle"],
                    trial_days=plan_data["trial_days"],
                    is_active=plan_data["is_active"],
                    is_popular=plan_data.get("is_popular", False)
                )
                
                session.add(plan)
                print(f"✓ Created {plan_data['tier'].value} plan: {plan_data['name']}")
            
            await session.commit()
            print("\n✓ All subscription plans seeded successfully!")
            
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(seed_subscription_plans())



