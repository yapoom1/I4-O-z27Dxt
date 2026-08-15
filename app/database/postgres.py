from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Clean database URL to remove query parameters unsupported by asyncpg (e.g. channel_binding, sslmode)
db_url = settings.DATABASE_URL
has_ssl_hint = False
if db_url:
    parsed = urlparse(db_url)
    query = parse_qs(parsed.query)
    
    # Check if SSL was requested in the original connection parameters
    if "sslmode" in query or "ssl" in query or ".neon.tech" in db_url:
        has_ssl_hint = True
        
    # Remove unsupported query parameters from the URI
    query.pop("channel_binding", None)
    query.pop("sslmode", None)
    
    new_query = urlencode(query, doseq=True)
    db_url = urlunparse(parsed._replace(query=new_query))

# Create database engine with asyncpg driver
connect_args = {}
if has_ssl_hint or "sslmode=require" in db_url or "ssl=require" in db_url:
    connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300, # Added: recycle connections every 5 mins to prevent Neon DB from dropping them
    connect_args=connect_args
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for SQLAlchemy declarative models
Base = declarative_base()

async def get_db_session() -> AsyncSession:
    """Dependency provider for AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_postgres():
    """Initialize PostgreSQL database by creating tables if they do not exist."""
    # Import all models to ensure they register on Base.metadata
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
    from app.deliveries.models import DeliveryRule, DeliveryAgent

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
