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

async def create_admins():
    async with AsyncSessionLocal() as db:
        print("--- Creating Super Admin ---")
        # 1. Create Super Admin if not present
        super_email = "superadmin@gubeera.com"
        stmt = select(User).where(User.email == super_email)
        res = await db.execute(stmt)
        super_admin = res.scalar_one_or_none()

        if not super_admin:
            hashed_super_pass = auth_service.hash_password("superpassword123")
            super_admin = User(
                name="System Super Admin",
                mobilenumber="+910000000000",
                email=super_email,
                password=hashed_super_pass,
                role="SUPER_ADMIN",
                status="ACTIVE",
                tenant_id=None
            )
            db.add(super_admin)
            await db.flush()
            print(f"[OK] Super Admin created with Email: {super_email}, Password: superpassword123")
        else:
            print(f"[INFO] Super Admin ({super_email}) already exists.")

        print("\n--- Creating Tenant & Tenant Admin for 'rritstores' ---")
        # 2. Create Tenant 'rritstores'
        tenant_name = "rritstores"
        stmt = select(Tenant).where(Tenant.business_name == tenant_name)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(business_name=tenant_name)
            db.add(tenant)
            await db.flush()
            print(f"[OK] Tenant '{tenant_name}' created with ID: {tenant.id}")
        else:
            print(f"[INFO] Tenant '{tenant_name}' already exists with ID: {tenant.id}")

        # 3. Create Tenant Admin user for rritstores
        admin_email = "rritstore64@gmail.com"
        admin_mobile = "+91 9585882972"
        stmt = select(User).where(
            (User.email == admin_email) | (User.mobilenumber == admin_mobile)
        )
        res = await db.execute(stmt)
        tenant_admin = res.scalar_one_or_none()

        if not tenant_admin:
            hashed_pass = auth_service.hash_password("123")
            tenant_admin = User(
                name="rritstores Admin",
                mobilenumber=admin_mobile,
                email=admin_email,
                password=hashed_pass,
                role="TENANT_ADMIN",
                status="ACTIVE",
                tenant_id=tenant.id
            )
            db.add(tenant_admin)
            await db.flush()
            print(f"[OK] Tenant Admin created for {tenant_name}:")
            print(f"   Email: {admin_email}")
            print(f"   Mobile: {admin_mobile}")
            print(f"   Password: 123")
            print(f"   Tenant ID: {tenant.id}")
        else:
            # Update role and tenant_id just in case
            tenant_admin.tenant_id = tenant.id
            tenant_admin.role = "TENANT_ADMIN"
            if not tenant_admin.password:
                tenant_admin.password = auth_service.hash_password("123")
            print(f"[INFO] Tenant Admin ({admin_email}) already exists. Updated role to TENANT_ADMIN and linked to Tenant {tenant.id}.")

        await db.commit()
        print("\nAll operations completed successfully!")

if __name__ == "__main__":
    asyncio.run(create_admins())
