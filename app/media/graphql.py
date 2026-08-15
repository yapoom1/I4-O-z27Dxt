import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum
import strawberry

from app.media.models import Media as DBMedia
from app.media.services import media_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.enum
class MediaTypeEnum(Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    PDF = "PDF"
    AUDIO = "AUDIO"
    OTHER = "OTHER"


@strawberry.type
class MediaType:
    """GraphQL representation of a Media record."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    entity_name: Optional[str] = strawberry.field(name="entityName")
    entity_id: Optional[uuid.UUID] = strawberry.field(name="entityId")
    file_path: str = strawberry.field(name="filePath")
    media_url: str = strawberry.field(name="mediaUrl")
    media_type: MediaTypeEnum = strawberry.field(name="mediaType")
    file_extension: Optional[str] = strawberry.field(name="fileExtension")
    alt_text: Optional[str] = strawberry.field(name="altText")
    meta_attributes: Optional[strawberry.scalars.JSON] = strawberry.field(name="metaAttributes")
    created_at: datetime
    updated_at: datetime

    def __init__(self, db_media: DBMedia):
        self.id = db_media.id
        self.tenant_id = db_media.tenant_id
        self.entity_name = db_media.entity_name
        self.entity_id = db_media.entity_id
        self.file_path = db_media.file_path
        self.media_url = db_media.media_url
        self.media_type = MediaTypeEnum(db_media.media_type)
        self.file_extension = db_media.file_extension
        self.alt_text = db_media.alt_text
        self.meta_attributes = db_media.meta_attributes
        self.created_at = db_media.created_at
        self.updated_at = db_media.updated_at


@strawberry.input
class CreateMediaInput:
    file_path: str = strawberry.field(name="filePath")
    media_url: str = strawberry.field(name="mediaUrl")
    media_type: MediaTypeEnum = strawberry.field(default=MediaTypeEnum.IMAGE, name="mediaType")
    file_extension: Optional[str] = strawberry.field(default=None, name="fileExtension")
    alt_text: Optional[str] = strawberry.field(default=None, name="altText")
    meta_attributes: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="metaAttributes")
    entity_name: Optional[str] = strawberry.field(default=None, name="entityName")
    entity_id: Optional[uuid.UUID] = strawberry.field(default=None, name="entityId")


@strawberry.input
class UpdateMediaInput:
    file_path: Optional[str] = strawberry.field(default=None, name="filePath")
    media_url: Optional[str] = strawberry.field(default=None, name="mediaUrl")
    media_type: Optional[MediaTypeEnum] = strawberry.field(default=None, name="mediaType")
    file_extension: Optional[str] = strawberry.field(default=None, name="fileExtension")
    alt_text: Optional[str] = strawberry.field(default=None, name="altText")
    meta_attributes: Optional[strawberry.scalars.JSON] = strawberry.field(default=None, name="metaAttributes")
    entity_name: Optional[str] = strawberry.field(default=None, name="entityName")
    entity_id: Optional[uuid.UUID] = strawberry.field(default=None, name="entityId")


@strawberry.type
class MediaQuery:
    @strawberry.field
    async def media_list(
        self,
        info: strawberry.Info,
        entity_name: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None
    ) -> List[MediaType]:
        """Fetch media records scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        db = info.context.db
        db_media_list = await media_service.get_media_list(
            db=db,
            tenant_id=tenant_id,
            entity_name=entity_name,
            entity_id=entity_id
        )
        return [MediaType(m) for m in db_media_list]

    @strawberry.field
    async def media(self, info: strawberry.Info, id: uuid.UUID) -> Optional[MediaType]:
        """Fetch a single media record by ID scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        db = info.context.db
        db_media = await media_service.get_media_by_id(db, tenant_id, id)
        return MediaType(db_media) if db_media else None


@strawberry.type
class MediaMutation:
    @strawberry.mutation
    async def create_media(self, info: strawberry.Info, input: CreateMediaInput) -> MediaType:
        """Register a new media record (Requires Admin permissions)."""
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        # 1. Authorize
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage media.")

        if not tenant_id:
            tenant_id = current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_media = await media_service.create_media(
            db=db,
            tenant_id=tenant_id,
            file_path=input.file_path,
            media_url=input.media_url,
            media_type=input.media_type.value,
            file_extension=input.file_extension,
            alt_text=input.alt_text,
            meta_attributes=input.meta_attributes,
            entity_name=input.entity_name,
            entity_id=input.entity_id,
            user_id=current_user.id
        )
        return MediaType(db_media)

    @strawberry.mutation
    async def update_media(self, info: strawberry.Info, id: uuid.UUID, input: UpdateMediaInput) -> MediaType:
        """Update fields on an existing media record (Requires Admin permissions)."""
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        # 1. Authorize
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage media.")

        if not tenant_id:
            tenant_id = current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        # Extract provided input fields
        kwargs = {}
        for field in [
            "file_path", "media_url", "file_extension", "alt_text",
            "meta_attributes", "entity_name", "entity_id"
        ]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        if input.media_type is not None:
            kwargs["media_type"] = input.media_type.value

        db = info.context.db
        db_media = await media_service.update_media(
            db=db,
            tenant_id=tenant_id,
            media_id=id,
            user_id=current_user.id,
            **kwargs
        )
        return MediaType(db_media)

    @strawberry.mutation
    async def delete_media(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete a media record scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        # 1. Authorize
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage media.")

        if not tenant_id:
            tenant_id = current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await media_service.delete_media(
            db=db,
            tenant_id=tenant_id,
            media_id=id,
            user_id=current_user.id
        )
