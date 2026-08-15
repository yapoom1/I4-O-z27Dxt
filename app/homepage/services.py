import uuid
import asyncio
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.homepage.models import HomepageConfig, HomepageSection
from app.products.products.services import product_service
from app.products.categories.services import category_service

class SectionResolver:
    """Dispatches resolution logic based on section type and dynamic source."""

    @staticmethod
    async def resolve_banner(section: HomepageSection) -> Dict[str, Any]:
        """Banners usually do not require database fetching, return config as is."""
        return section.config.get("banners", [])

    @staticmethod
    async def resolve_products(db: AsyncSession, tenant_id: uuid.UUID, section: HomepageSection) -> List[Dict[str, Any]]:
        """Resolve products based on manual selection or dynamic rules."""
        source_type = section.config.get("source_type", "manual")
        products = []
        
        if source_type == "manual":
            product_ids_str = section.config.get("product_ids", [])
            product_ids = [uuid.UUID(pid) for pid in product_ids_str if pid]
            if product_ids:
                products = await product_service.get_product_by_ids(db, tenant_id, product_ids)
        elif source_type == "dynamic":
            source = section.config.get("source")
            limit = section.config.get("limit", 10)
            
            if source == "best_sellers":
                products = await product_service.get_best_sellers(db, tenant_id, limit)
            elif source == "new_arrivals":
                products = await product_service.get_new_arrivals(db, tenant_id, limit)
            elif source == "category":
                category_id_str = section.config.get("category_id")
                if category_id_str:
                    products = await product_service.get_products_by_category(
                        db, tenant_id, uuid.UUID(category_id_str), limit
                    )
                    
        # Return basic product info suitable for homepage cards
        return [
            {
                "id": str(p.id),
                "title": p.title,
                "subtitle": p.subtitle,
                "sku": p.sku,
                "thumbnail_media_id": str(p.thumbnail_media_id) if p.thumbnail_media_id else None
            } for p in products
        ]

    @staticmethod
    async def resolve_categories(db: AsyncSession, tenant_id: uuid.UUID, section: HomepageSection) -> List[Dict[str, Any]]:
        """Resolve categories from a list of IDs."""
        category_ids_str = section.config.get("category_ids", [])
        categories = []
        # Use asyncio.gather for parallel fetching
        
        async def fetch_category(cat_id_str: str):
            if not cat_id_str:
                return None
            return await category_service.get_category_by_id(db, tenant_id, uuid.UUID(cat_id_str))
            
        tasks = [fetch_category(cid) for cid in category_ids_str]
        fetched_categories = await asyncio.gather(*tasks)
        
        for cat in fetched_categories:
            if cat:
                categories.append({
                    "id": str(cat.id),
                    "title": cat.title,
                    "thumbnail_media_id": str(cat.thumbnail_media_id) if cat.thumbnail_media_id else None
                })
        return categories

    @staticmethod
    async def resolve_promo(section: HomepageSection) -> Dict[str, Any]:
        """Return promo config as is."""
        return section.config


class HomepageService:
    """Service orchestrating homepage resolution and orchestration."""
    
    @staticmethod
    async def resolve_homepage(db: AsyncSession, tenant_id: uuid.UUID, config: HomepageConfig) -> Dict[str, Any]:
        """Resolve all sections in the homepage config."""
        # Sort sections by order
        sorted_sections = sorted(config.sections, key=lambda s: s.order)
        
        resolved_sections = []
        
        for section in sorted_sections:
            resolved_data = None
            if section.type == "banner":
                resolved_data = await SectionResolver.resolve_banner(section)
            elif section.type == "products":
                resolved_data = await SectionResolver.resolve_products(db, tenant_id, section)
            elif section.type == "categories":
                resolved_data = await SectionResolver.resolve_categories(db, tenant_id, section)
            elif section.type == "promo":
                resolved_data = await SectionResolver.resolve_promo(section)
            else:
                resolved_data = section.config
                
            resolved_sections.append({
                "id": str(section.id),
                "type": section.type,
                "title": section.title,
                "order": section.order,
                "data": resolved_data
            })
            
        return {
            "tenant_id": str(config.tenant_id),
            "version": config.version,
            "status": config.status,
            "sections": resolved_sections,
            "updated_at": config.updated_at.isoformat()
        }

homepage_service = HomepageService()
