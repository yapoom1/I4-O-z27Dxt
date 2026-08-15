import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.postgres import AsyncSessionLocal
from app.tenants.services import tenant_service
from sqlalchemy.future import select

# Import all models so SQLAlchemy relationship mappers resolve correctly
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


async def set_shiprocket_credentials(tenant_id_str: str, email: str, password: str):
    async with AsyncSessionLocal() as db:
        stmt = select(Tenant).where(Tenant.id == tenant_id_str)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()

        if not tenant:
            print(f"[ERROR] Tenant '{tenant_id_str}' not found in database.")
            return

        updated_tenant = await tenant_service.update_tenant(
            db=db,
            tenant_id=tenant.id,
            shiprocket_email=email,
            shiprocket_password=password
        )
        print(f"[SUCCESS] Successfully updated Shiprocket credentials for tenant ID: {tenant.id}")
        print(f"   Email: {updated_tenant.shiprocket_email}")
        print(f"   Password: Encrypted safely in DB")
        print(f"   Cached token reset successfully.")

if __name__ == "__main__":
    # =========================================================
    # EDIT THESE 3 VARIABLES WITH YOUR SHIPROCKET DETAILS
    # =========================================================
    TARGET_TENANT = "4c7b9c85-0963-49ba-bd2f-7776a0be4b71"  # Replace with your Tenant ID
    SHIPROCKET_EMAIL = "roydenlal@gmail.com"  # Replace with your Shiprocket Email
    SHIPROCKET_PASSWORD = "FHM3X!nZT47NG5oD7MKe7sRfsDdqX7U2"  # Replace with your Shiprocket Password
    # =========================================================

    if SHIPROCKET_EMAIL == "your_email@example.com":
        print("[WARNING] Please edit update_tenant_shiprocket.py with your real Shiprocket email and password first!")
    else:
        print(f"Updating Shiprocket credentials for tenant '{TARGET_TENANT}'...")
        asyncio.run(set_shiprocket_credentials(TARGET_TENANT, SHIPROCKET_EMAIL, SHIPROCKET_PASSWORD))
