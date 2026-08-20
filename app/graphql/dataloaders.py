import uuid
from typing import List, Optional
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.media.models import Media
from app.products.categories.mongo_models import Category as MongoCategory
from app.products.products.mongo_models import Product as DBProduct
from app.products.pricing.models import ProductPrice, PricingType

async def load_pricing_types_by_ids(keys: List[uuid.UUID], db: AsyncSession, tenant_id: uuid.UUID) -> List[Optional[PricingType]]:
    """Batch load PricingType by their IDs."""
    stmt = select(PricingType).where(
        PricingType.id.in_(keys),
        PricingType.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    pt_records = res.scalars().all()
    pt_map = {pt.id: pt for pt in pt_records}
    return [pt_map.get(key) for key in keys]

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

async def load_product_prices_by_product_ids(keys: List[uuid.UUID], db: AsyncSession, tenant_id: uuid.UUID) -> List[List[ProductPrice]]:
    """Batch load all product prices by product IDs."""
    stmt = select(ProductPrice).join(
        PricingType, ProductPrice.pricing_type_id == PricingType.id
    ).where(
        ProductPrice.product_id.in_(keys),
        PricingType.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.product_id].append(row)
    return [grouped.get(key, []) for key in keys]

async def load_children_by_parent_ids(keys: List[uuid.UUID], tenant_id: uuid.UUID) -> List[List[DBProduct]]:
    """Batch load child products by their parent IDs."""
    if not keys:
        return []
    children = await DBProduct.find({"parent_id": {"$in": keys}, "tenant_id": tenant_id}).sort("-created_at").to_list()
    grouped = defaultdict(list)
    for c in children:
        if c.parent_id:
            grouped[c.parent_id].append(c)
    return [grouped.get(key, []) for key in keys]

async def load_media_by_entity_ids(keys: List[uuid.UUID], db: AsyncSession, tenant_id: uuid.UUID) -> List[List[Media]]:
    """Batch load Media by entity ID (product)."""
    stmt = select(Media).where(
        Media.entity_id.in_(keys),
        Media.entity_name == "product",
        Media.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    media_records = res.scalars().all()
    grouped = defaultdict(list)
    for m in media_records:
        if m.entity_id:
            grouped[m.entity_id].append(m)
    return [grouped.get(key, []) for key in keys]

class DataLoaders:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        from strawberry.dataloader import DataLoader
        self.db = db
        self.tenant_id = tenant_id
        
        self.media_loader = DataLoader(load_fn=self._load_media)
        self.category_loader = DataLoader(load_fn=self._load_categories)
        self.selling_price_loader = DataLoader(load_fn=self._load_selling_price)
        self.effective_price_loader = DataLoader(load_fn=self._load_effective_prices)
        self.product_prices_loader = DataLoader(load_fn=self._load_product_prices)
        self.children_loader = DataLoader(load_fn=self._load_children)
        self.product_media_loader = DataLoader(load_fn=self._load_product_media)
        self.pricing_type_loader = DataLoader(load_fn=self._load_pricing_types)

    async def _load_media(self, keys: List[uuid.UUID]) -> List[Optional[Media]]:
        return await load_media_by_ids(keys, self.db, self.tenant_id)

    async def _load_categories(self, keys: List[uuid.UUID]) -> List[Optional[MongoCategory]]:
        return await load_categories_by_ids(keys, self.tenant_id)

    async def _load_selling_price(self, keys: List[uuid.UUID]) -> List[Optional[float]]:
        return await load_selling_price_by_product_ids(keys, self.db, self.tenant_id)

    async def _load_effective_prices(self, keys: List[tuple]) -> List[float]:
        return await load_effective_prices_by_keys(keys, self.db, self.tenant_id)

    async def _load_product_prices(self, keys: List[uuid.UUID]) -> List[List[ProductPrice]]:
        return await load_product_prices_by_product_ids(keys, self.db, self.tenant_id)

    async def _load_children(self, keys: List[uuid.UUID]) -> List[List[DBProduct]]:
        return await load_children_by_parent_ids(keys, self.tenant_id)

    async def _load_product_media(self, keys: List[uuid.UUID]) -> List[List[Media]]:
        return await load_media_by_entity_ids(keys, self.db, self.tenant_id)

    async def _load_pricing_types(self, keys: List[uuid.UUID]) -> List[Optional[PricingType]]:
        return await load_pricing_types_by_ids(keys, self.db, self.tenant_id)
