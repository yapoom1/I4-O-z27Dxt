import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.postgres import AsyncSessionLocal
from app.database.mongodb import init_mongodb

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

from app.products.categories.models import Category as PGCategory
from app.products.products.models import Product as PGProduct, ProductStock as PGStock, ProductAttributeValue as PGAttrVal, ProductGroupLink as PGGroupLink
from app.products.products.models import Attribute as PGAttribute, AttributeValue as PGAttributeValue, ProductGroup as PGProductGroup

from app.products.categories.mongo_models import Category as MongoCategory
from app.products.products.mongo_models import (
    Product as MongoProduct,
    ProductStockModel,
    ProductAttributeModel,
    ProductGroupLinkModel,
    Attribute as MongoAttribute,
    AttributeValueModel,
    ProductGroup as MongoProductGroup
)

async def migrate():
    # Initialize MongoDB
    await init_mongodb()
    
    async with AsyncSessionLocal() as db:
        print("Starting migration...")
        
        # 1. Migrate Attributes
        print("Migrating Attributes...")
        res = await db.execute(select(PGAttribute).options(selectinload(PGAttribute.values)))
        pg_attrs = res.scalars().all()
        for pg_attr in pg_attrs:
            values = [AttributeValueModel(id=v.id, value=v.value, hex_code=v.hex_code, created_at=v.created_at) for v in pg_attr.values]
            m_attr = MongoAttribute(
                _id=pg_attr.id,
                tenant_id=pg_attr.tenant_id,
                name=pg_attr.name,
                display_name=pg_attr.display_name,
                values=values,
                created_at=pg_attr.created_at
            )
            await m_attr.save()
            print(f"  Inserted Attribute {pg_attr.name}")
            
        # 2. Migrate Product Groups
        print("Migrating Product Groups...")
        res = await db.execute(select(PGProductGroup))
        pg_groups = res.scalars().all()
        for pg_group in pg_groups:
            m_group = MongoProductGroup(
                _id=pg_group.id,
                tenant_id=pg_group.tenant_id,
                name=pg_group.name,
                description=pg_group.description,
                created_at=pg_group.created_at,
                updated_at=pg_group.updated_at
            )
            await m_group.save()
            print(f"  Inserted Group {pg_group.name}")
            
        # 3. Migrate Categories
        print("Migrating Categories...")
        res = await db.execute(select(PGCategory))
        pg_categories = res.scalars().all()
        for pg_cat in pg_categories:
            m_cat = MongoCategory(
                _id=pg_cat.id,
                tenant_id=pg_cat.tenant_id,
                parent_id=pg_cat.parent_id,
                title=pg_cat.title,
                subtitle=pg_cat.subtitle,
                description=pg_cat.description,
                description_long=pg_cat.description_long,
                sku=pg_cat.sku,
                thumbnail_media_id=pg_cat.thumbnail_media_id,
                created_at=pg_cat.created_at,
                updated_at=pg_cat.updated_at
            )
            await m_cat.save()
            print(f"  Inserted Category {pg_cat.id}")

        # 4. Migrate Products with embedded relations
        print("Migrating Products...")
        res = await db.execute(select(PGProduct).options(
            selectinload(PGProduct.stock),
            selectinload(PGProduct.categories),
            selectinload(PGProduct.attributes).selectinload(PGAttrVal.attribute_value).selectinload(PGAttributeValue.attribute),
            selectinload(PGProduct.groups).selectinload(PGGroupLink.group)
        ))
        pg_products = res.scalars().unique().all()
        
        for pg_prod in pg_products:
            # Prepare Embedded Stock
            stock_embedded = None
            if pg_prod.stock:
                stock_embedded = ProductStockModel(
                    stock=pg_prod.stock.stock,
                    updated_at=pg_prod.stock.updated_at
                )
                
            # Prepare Embedded Attributes
            attrs_embedded = []
            for pav in pg_prod.attributes:
                if pav.attribute_value and pav.attribute_value.attribute:
                    attrs_embedded.append(ProductAttributeModel(
                        attribute_name=pav.attribute_value.attribute.name,
                        attribute_value=pav.attribute_value.value,
                        hex_code=pav.attribute_value.hex_code,
                        pricing_type_id=pav.pricing_type_id
                    ))
                    
            # Prepare Embedded Groups
            groups_embedded = []
            for gl in pg_prod.groups:
                if gl.group:
                    groups_embedded.append(ProductGroupLinkModel(
                        group_id=gl.group.id,
                        group_name=gl.group.name
                    ))
                    
            category_ids = [c.id for c in pg_prod.categories]

            m_prod = MongoProduct(
                _id=pg_prod.id,
                tenant_id=pg_prod.tenant_id,
                parent_id=pg_prod.parent_id,
                category_ids=category_ids,
                title=pg_prod.title,
                subtitle=pg_prod.subtitle,
                description=pg_prod.description,
                description_long=pg_prod.description_long,
                sku=pg_prod.sku,
                product_type=pg_prod.product_type,
                thumbnail_media_id=pg_prod.thumbnail_media_id,
                stock=stock_embedded,
                attributes=attrs_embedded,
                groups=groups_embedded,
                created_at=pg_prod.created_at,
                updated_at=pg_prod.updated_at
            )
            await m_prod.save()
            print(f"  Inserted Product {pg_prod.id}")

        print("Migration Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
