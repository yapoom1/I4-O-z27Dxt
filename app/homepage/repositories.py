import uuid
from typing import Optional
from datetime import datetime
from app.homepage.models import HomepageConfig, HomepageSection

class HomepageRepository:
    """Repository handling Beanie MongoDB operations for Homepage Configuration."""

    @staticmethod
    async def get_by_tenant_id(tenant_id: uuid.UUID) -> Optional[HomepageConfig]:
        """Fetch the homepage configuration for a specific tenant."""
        return await HomepageConfig.find_one({"tenant_id": tenant_id})

    @staticmethod
    async def save(config: HomepageConfig) -> HomepageConfig:
        """Save or update a homepage configuration."""
        config.updated_at = datetime.utcnow()
        await config.save()
        return config

    @staticmethod
    async def delete_section(tenant_id: uuid.UUID, section_id: uuid.UUID) -> bool:
        """Remove a specific section from a tenant's homepage configuration."""
        config = await HomepageRepository.get_by_tenant_id(tenant_id)
        if not config:
            return False
            
        initial_count = len(config.sections)
        config.sections = [s for s in config.sections if s.id != section_id]
        
        if len(config.sections) < initial_count:
            config.version += 1
            config.updated_at = datetime.utcnow()
            await config.save()
            return True
            
        return False

homepage_repository = HomepageRepository()
