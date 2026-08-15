import asyncio
import sys
import os

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy.future import select
from app.database.postgres import AsyncSessionLocal
from app.auth.services import auth_service

# Import all models to ensure they are registered with SQLAlchemy's Base metadata
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
from app.subscriptions.models import (
    SubscriptionPlan, SubscriptionFeatures,
    TenantSubscription, TenantSubscriptionPayment,
)


async def main():
    print("=== SEEDING SUPER ADMIN ===")
    async with AsyncSessionLocal() as db:
        # 1. Fetch or create a default system tenant
        stmt_tenant = select(Tenant).limit(1)
        res_tenant = await db.execute(stmt_tenant)
        tenant = res_tenant.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(business_name="System Default Tenant")
            db.add(tenant)
            await db.flush()
            print(f"Created default system tenant: {tenant.business_name} (ID: {tenant.id})")
        else:
            print(f"Using existing tenant: {tenant.business_name} (ID: {tenant.id})")

        # 2. Check if a Super Admin already exists in this tenant
        stmt_admin = select(User).where(
            (User.tenant_id == tenant.id) &
            (User.role == "SUPER_ADMIN")
        )
        res_admin = await db.execute(stmt_admin)
        super_admin = res_admin.scalar_one_or_none()

        password="1234"
        hashed_pwd = auth_service.hash_password(password)
        super_admin = User(
            name="Suhail",
            mobilenumber="9865150759",
            email="suhail@gmail.com",
            password=hashed_pwd,
            role="SUPER_ADMIN",
            tenant_id=tenant.id,
            status="ACTIVE"
        )
        db.add(super_admin)
        await db.commit()
        print(f"Created Super Admin: {super_admin.name} (ID: {super_admin.id})")
        print("Credentials:")
        print(f"  Email: {super_admin.email}")
        print(f"  Password: {super_admin.password}and original password:{password}" )
        print(f"  Tenant ID: {tenant.id}")
    '''else:
        print(f"Super Admin already exists: {super_admin.name} (ID: {super_admin.id})")
        print("Credentials:")
        print(f"  Email: {super_admin.email}")
        print(f"  Tenant ID: {tenant.id}")'''
print("=== SEEDING COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(main())