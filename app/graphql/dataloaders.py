import uuid
from typing import List, Optional
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.media.models import Media
from app.products.categories.mongo_models import Category as MongoCategory
from app.products.pricing.models import ProductPrice, PricingType

async def load_media_by_ids(keys: List[uuid.UUID], db: AsyncSession, tenant_id: uuid.UUID) -> List[Optional[Media]]:
    """Batch load Media by their IDs."""
    stmt = select(Media).where(
        Media.id.in_(keys),
        Media.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    media_records = res.scalars().all()
    media_map = {m.id: m for m in media_records}
    return [media_map.get(key) for key in keys]

async def load_categories_by_ids(keys: List[uuid.UUID], tenant_id: uuid.UUID) -> List[Optional[MongoCategory]]:
    """Batch load Categories by their IDs using Beanie (MongoDB)."""
    if not keys:
        return []
    categories = await MongoCategory.find({"_id": {"$in": keys}, "tenant_id": tenant_id}).to_list()
    cat_map = {c.id: c for c in categories}
    return [cat_map.get(key) for key in keys]

async def load_selling_price_by_product_ids(keys: List[uuid.UUID], db: AsyncSession, tenant_id: uuid.UUID) -> List[Optional[float]]:
    """Batch load selling prices by product IDs."""
    stmt = select(ProductPrice.product_id, ProductPrice.price).join(
        PricingType, ProductPrice.pricing_type_id == PricingType.id
    ).where(
        ProductPrice.product_id.in_(keys),
        PricingType.tenant_id == tenant_id,
        PricingType.type == "selling_price"
    )
    res = await db.execute(stmt)
    rows = res.all()
    price_map = {row.product_id: float(row.price) for row in rows}
    return [price_map.get(key) for key in keys]

async def load_effective_prices_by_keys(keys: List[tuple], db: AsyncSession, tenant_id: uuid.UUID) -> List[float]:
    """Batch calculate effective prices."""
    from app.products.pricing.services import pricing_service
    decimals = await pricing_service.batch_get_effective_prices(db, tenant_id, keys)
    return [float(d) for d in decimals]

class DataLoaders:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        from strawberry.dataloader import DataLoader
        self.db = db
        self.tenant_id = tenant_id
        
        self.media_loader = DataLoader(load_fn=self._load_media)
        self.category_loader = DataLoader(load_fn=self._load_categories)
        self.selling_price_loader = DataLoader(load_fn=self._load_selling_price)
        self.effective_price_loader = DataLoader(load_fn=self._load_effective_prices)

    async def _load_media(self, keys: List[uuid.UUID]) -> List[Optional[Media]]:
        return await load_media_by_ids(keys, self.db, self.tenant_id)

    async def _load_categories(self, keys: List[uuid.UUID]) -> List[Optional[MongoCategory]]:
        return await load_categories_by_ids(keys, self.tenant_id)

    async def _load_selling_price(self, keys: List[uuid.UUID]) -> List[Optional[float]]:
        return await load_selling_price_by_product_ids(keys, self.db, self.tenant_id)

    async def _load_effective_prices(self, keys: List[tuple]) -> List[float]:
        return await load_effective_prices_by_keys(keys, self.db, self.tenant_id)
