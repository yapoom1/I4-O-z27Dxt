import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import settings and metadata
from app.config import settings
from app.database.postgres import Base
from app.users.models import User, UserAddress
from app.tenants.models import Tenant, TenantDomain, SystemDomain
from app.products.products.models import Product, Attribute, AttributeValue, ProductAttributeValue, ProductGroup, ProductGroupLink, ProductStock, ProductShipping
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
from app.deliveries.models import DeliveryRule, DeliveryAgent


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Create an async Engine and run online migrations."""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
