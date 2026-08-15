import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.future import select

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

from app.auth.services import auth_service

# ==========================================
# EDIT THESE VARIABLES FOR YOUR NEW TENANT
# ==========================================
TENANT_BUSINESS_NAME = ""
ADMIN_NAME = "Vathukadai Admin"
ADMIN_EMAIL = "vathukadi@gmail.com"
ADMIN_MOBILE = "+91 9999999999"
ADMIN_PASSWORD = "123"
# ==========================================

async def create_new_tenant():
    async with AsyncSessionLocal() as db:
        print(f"--- Creating Tenant '{TENANT_BUSINESS_NAME}' ---")
        
        # 1. Check if Tenant exists
        stmt = select(Tenant).where(Tenant.business_name == TENANT_BUSINESS_NAME)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()   

        if not tenant:
            tenant = Tenant(business_name=TENANT_BUSINESS_NAME)
            db.add(tenant)
            await db.flush()
            print(f"[OK] Tenant '{TENANT_BUSINESS_NAME}' created with ID: {tenant.id}")
        else:
            print(f"[INFO] Tenant '{TENANT_BUSINESS_NAME}' already exists with ID: {tenant.id}")

        # 2. Check if Admin user exists
        stmt = select(User).where(
            (User.email == ADMIN_EMAIL) | (User.mobilenumber == ADMIN_MOBILE)
        )
        res = await db.execute(stmt)
        tenant_admin = res.scalar_one_or_none()

        if not tenant_admin:
            hashed_pass = auth_service.hash_password(ADMIN_PASSWORD)
            tenant_admin = User(
                name=ADMIN_NAME,
                mobilenumber=ADMIN_MOBILE,
                email=ADMIN_EMAIL,
                password=hashed_pass,
                role="TENANT_ADMIN",
                status="ACTIVE",
                tenant_id=tenant.id
            )
            db.add(tenant_admin)
            await db.flush()
            print(f"[OK] Tenant Admin created for {TENANT_BUSINESS_NAME}:")
            print(f"   Name: {ADMIN_NAME}")
            print(f"   Email: {ADMIN_EMAIL}")
            print(f"   Mobile: {ADMIN_MOBILE}")
            print(f"   Password: {ADMIN_PASSWORD}")
            print(f"   Tenant ID: {tenant.id}")
        else:
            # Update role and tenant_id just in case
            tenant_admin.tenant_id = tenant.id
            tenant_admin.role = "TENANT_ADMIN"
            if not tenant_admin.password:
                tenant_admin.password = auth_service.hash_password(ADMIN_PASSWORD)
            print(f"[INFO] User ({ADMIN_EMAIL} / {ADMIN_MOBILE}) already exists. Updated role to TENANT_ADMIN and linked to Tenant {tenant.id}.")

        await db.commit()
        print("\nAll operations completed successfully!")

if __name__ == "__main__":
    asyncio.run(create_new_tenant())
