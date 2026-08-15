import sys
import os
import asyncio
from sqlalchemy.future import select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.postgres import AsyncSessionLocal

# Import all SQLAlchemy models so relationships resolve correctly
from app.users.models import User, UserAddress
from app.tenants.models import Tenant, TenantDomain, SystemDomain
from app.products.products.models import Product, Attribute, AttributeValue, ProductAttributeValue, ProductGroup, ProductGroupLink, ProductStock
from app.products.categories.models import Category, ProductCategory
from app.products.pricing.models import PricingType, ProductPrice, ProductPricingRule
from app.payments.models import PaymentGateway, TenantPaymentGateway, TenantCommission
from app.media.models import Media
from app.promotions.models import Coupon, CouponUsage
from app.orders.models import Order, OrderItem, OrderPayment, OrderReturn, OrderReturnItem
from app.reviews.models import ProductReview, OrderReview, CompanyReview
from app.wallet.models import UserWallet, UserWalletTransaction
from app.referral.models import UserReferral, UserReferralHistory, UserReferralPointsTransactionHistory

async def fix_pricing():
    async with AsyncSessionLocal() as db:
        print("--- Fixing Pricing for All Tenants ---")
        
        # Find all tenants
        stmt = select(Tenant)
        res = await db.execute(stmt)
        tenants = res.scalars().all()

        for tenant in tenants:
            # Check if PricingType already exists
            stmt = select(PricingType).where(PricingType.tenant_id == tenant.id)
            res = await db.execute(stmt)
            existing_types = res.scalars().all()
            existing_names = [t.type for t in existing_types]

            if "Selling Price" in existing_names:
                print(f"'Selling Price' already exists for {tenant.business_name}.")
            else:
                print(f"No 'Selling Price' found for {tenant.business_name}. Creating...")
                db.add(PricingType(tenant_id=tenant.id, type="Selling Price"))
                print(f"[OK] Successfully created 'Selling Price' for {tenant.business_name}!")
                
            if "MRP" in existing_names:
                print(f"'MRP' already exists for {tenant.business_name}.")
            else:
                print(f"No 'MRP' found for {tenant.business_name}. Creating...")
                db.add(PricingType(tenant_id=tenant.id, type="MRP"))
                print(f"[OK] Successfully created 'MRP' for {tenant.business_name}!")

            await db.commit()
            
        print("\nAll done! Please refresh your Admin Panel and try updating the price again.")

if __name__ == "__main__":
    asyncio.run(fix_pricing())
