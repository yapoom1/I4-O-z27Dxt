from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.utils.audit import AuditLog

# Monkey-patch Motor client to support Beanie's metadata append on newer Motor versions
if not hasattr(AsyncIOMotorClient, "append_metadata"):
    AsyncIOMotorClient.append_metadata = lambda self, *args, **kwargs: None

async def init_mongodb():
    """Initialize MongoDB connection pool and Beanie documents."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Use database name from configuration settings
    db = client[settings.MONGODB_DB_NAME]
        
    from app.homepage.models import HomepageConfig
    from app.products.categories.mongo_models import Category as MongoCategory
    from app.products.products.mongo_models import Product as MongoProduct, Attribute as MongoAttribute, ProductGroup as MongoProductGroup
    await init_beanie(
        database=db,
        document_models=[AuditLog, HomepageConfig, MongoCategory, MongoProduct, MongoAttribute, MongoProductGroup]
    )
    return client
