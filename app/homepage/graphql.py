import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import strawberry

from app.homepage.models import HomepageConfig as DBHomepageConfig, HomepageSection as DBHomepageSection
from app.homepage.repositories import homepage_repository
from app.homepage.services import homepage_service
from app.database.redis import redis_client
from app.utils.exceptions import UnauthorizedError, GuberaException

def _get_cache_key(tenant_id: uuid.UUID) -> str:
    return f"homepage:{str(tenant_id)}"

def check_admin(info: strawberry.Info):
    user = info.context.user
    if not user:
        raise UnauthorizedError("Authentication required.")
    if user.status != "ACTIVE":
        raise UnauthorizedError("User account is inactive.")
    if user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
        raise UnauthorizedError("Insufficient permissions. Admin role required.")

@strawberry.type
class HomepageSectionType:
    id: uuid.UUID
    type: str
    title: str
    order: int
    config: strawberry.scalars.JSON

    @classmethod
    def from_pydantic(cls, section: DBHomepageSection) -> "HomepageSectionType":
        return cls(
            id=section.id,
            type=section.type,
            title=section.title,
            order=section.order,
            config=section.config
        )

@strawberry.type
class HomepageConfigType:
    tenant_id: uuid.UUID
    version: int
    status: str
    sections: List[HomepageSectionType]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, config: DBHomepageConfig) -> "HomepageConfigType":
        return cls(
            tenant_id=config.tenant_id,
            version=config.version,
            status=config.status,
            sections=[HomepageSectionType.from_pydantic(s) for s in config.sections],
            created_at=config.created_at,
            updated_at=config.updated_at
        )

@strawberry.input
class HomepageSectionInput:
    type: str
    title: str
    config: strawberry.scalars.JSON
    id: Optional[uuid.UUID] = strawberry.field(default=None)
    order: int = 0

    def to_pydantic(self) -> DBHomepageSection:
        kwargs = {
            "type": self.type,
            "title": self.title,
            "order": self.order,
            "config": self.config
        }
        if self.id:
            kwargs["id"] = self.id
        return DBHomepageSection(**kwargs)

@strawberry.input
class CreateOrUpdateHomepageConfigInput:
    status: str
    sections: List[HomepageSectionInput]

@strawberry.input
class UpdateHomepageConfigInput:
    status: Optional[str] = strawberry.field(default=None)
    sections: Optional[List[HomepageSectionInput]] = strawberry.field(default=None)

@strawberry.type
class HomepageQuery:
    @strawberry.field
    async def published_homepage(self, info: strawberry.Info) -> Optional[strawberry.scalars.JSON]:
        """Fetch and resolve the published homepage configuration (Customer-facing)."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise GuberaException("Tenant context is missing. Provide X-Tenant-ID header.", code="TENANT_NOT_FOUND")

        cache_key = _get_cache_key(tenant_id)
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                pass

        db = info.context.db
        config = await homepage_repository.get_by_tenant_id(tenant_id)
        if not config or config.status != "published":
            return None

        resolved_payload = await homepage_service.resolve_homepage(db, tenant_id, config)
        
        # Cache the resolved response
        await redis_client.set(cache_key, json.dumps(resolved_payload), expire_seconds=3600)
        
        return resolved_payload

    @strawberry.field
    async def homepage_config(self, info: strawberry.Info) -> Optional[HomepageConfigType]:
        """Fetch the raw homepage configuration (Admin API)."""
        check_admin(info)
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise GuberaException("Tenant context is missing.", code="TENANT_NOT_FOUND")

        config = await homepage_repository.get_by_tenant_id(tenant_id)
        if not config:
            return None
        return HomepageConfigType.from_db(config)


@strawberry.type
class HomepageMutation:
    @strawberry.mutation
    async def create_or_update_homepage_config(self, info: strawberry.Info, input: CreateOrUpdateHomepageConfigInput) -> HomepageConfigType:
        """Create or overwrite the tenant's homepage configuration (Admin API)."""
        check_admin(info)
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise GuberaException("Tenant context is missing.", code="TENANT_NOT_FOUND")

        config = await homepage_repository.get_by_tenant_id(tenant_id)
        pydantic_sections = [s.to_pydantic() for s in input.sections]
        
        if config:
            config.status = input.status
            config.sections = pydantic_sections
            config.version += 1
        else:
            config = DBHomepageConfig(
                tenant_id=tenant_id,
                status=input.status,
                sections=pydantic_sections
            )
            
        saved_config = await homepage_repository.save(config)
        
        # Invalidate cache
        await redis_client.delete(_get_cache_key(tenant_id))
        
        return HomepageConfigType.from_db(saved_config)

    @strawberry.mutation
    async def update_homepage_config(self, info: strawberry.Info, input: UpdateHomepageConfigInput) -> HomepageConfigType:
        """Update specific attributes of the tenant's homepage configuration (Admin API)."""
        check_admin(info)
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise GuberaException("Tenant context is missing.", code="TENANT_NOT_FOUND")

        config = await homepage_repository.get_by_tenant_id(tenant_id)
        if not config:
            raise GuberaException("Homepage configuration not found.", code="NOT_FOUND")
            
        modified = False
        if input.status is not None:
            config.status = input.status
            modified = True
            
        if input.sections is not None:
            config.sections = [s.to_pydantic() for s in input.sections]
            modified = True
            
        if modified:
            config.version += 1
            config = await homepage_repository.save(config)
            await redis_client.delete(_get_cache_key(tenant_id))
            
        return HomepageConfigType.from_db(config)

    @strawberry.mutation
    async def delete_homepage_section(self, info: strawberry.Info, section_id: uuid.UUID) -> bool:
        """Delete a specific section from the homepage configuration (Admin API)."""
        check_admin(info)
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise GuberaException("Tenant context is missing.", code="TENANT_NOT_FOUND")

        success = await homepage_repository.delete_section(tenant_id, section_id)
        if not success:
            raise GuberaException("Section not found or homepage configuration does not exist.", code="NOT_FOUND")
            
        await redis_client.delete(_get_cache_key(tenant_id))
        return True
