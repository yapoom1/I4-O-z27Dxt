import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.media.models import Media
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class MediaService:
    """Service handling PostgreSQL operations for Media and Beanie audit logging."""

    @staticmethod
    async def get_media_list(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entity_name: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None
    ) -> List[Media]:
        """Fetch a list of media records scoped to a tenant, with optional entity filters."""
        stmt = select(Media).where(Media.tenant_id == tenant_id)
        
        if entity_name:
            stmt = stmt.where(Media.entity_name == entity_name.strip().lower())
            
        if entity_id:
            stmt = stmt.where(Media.entity_id == entity_id)
            
        stmt = stmt.order_by(Media.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_media_by_id(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        media_id: uuid.UUID
    ) -> Optional[Media]:
        """Fetch a single media record by ID scoped to a tenant."""
        stmt = select(Media).where(
            (Media.id == media_id) &
            (Media.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_media(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_path: str,
        media_url: str,
        media_type: str = "IMAGE",
        file_extension: Optional[str] = None,
        alt_text: Optional[str] = None,
        meta_attributes: Optional[Dict[str, Any]] = None,
        entity_name: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Media:
        """Create a new media record scoped to a tenant."""
        normalized_entity_name = entity_name.strip().lower() if entity_name else None

        media = Media(
            tenant_id=tenant_id,
            entity_name=normalized_entity_name,
            entity_id=entity_id,
            file_path=file_path,
            media_url=media_url,
            media_type=media_type.strip().upper(),
            file_extension=file_extension.strip().lower() if file_extension else None,
            alt_text=alt_text,
            meta_attributes=meta_attributes
        )
        db.add(media)
        await db.commit()
        await db.refresh(media)

        # Log to MongoDB
        await log_audit_event(
            action="MEDIA_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "media_id": str(media.id),
                "media_type": media.media_type,
                "entity_name": normalized_entity_name,
                "entity_id": str(entity_id) if entity_id else None
            }
        )

        return media

    @staticmethod
    async def update_media(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        media_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Media:
        """Update an existing media record."""
        media = await MediaService.get_media_by_id(db, tenant_id, media_id)
        if not media:
            raise ValidationError("Media record not found or belongs to another tenant.")

        if "entity_name" in kwargs:
            kwargs["entity_name"] = kwargs["entity_name"].strip().lower() if kwargs["entity_name"] else None
            
        if "media_type" in kwargs and kwargs["media_type"]:
            kwargs["media_type"] = kwargs["media_type"].strip().upper()
            
        if "file_extension" in kwargs:
            kwargs["file_extension"] = kwargs["file_extension"].strip().lower() if kwargs["file_extension"] else None

        for field, value in kwargs.items():
            setattr(media, field, value)

        await db.commit()
        await db.refresh(media)

        # Log to MongoDB
        await log_audit_event(
            action="MEDIA_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "media_id": str(media_id),
                "updated_fields": list(kwargs.keys())
            }
        )

        return media

    @staticmethod
    async def delete_media(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        media_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a media record from the database."""
        media = await MediaService.get_media_by_id(db, tenant_id, media_id)
        if not media:
            raise ValidationError("Media record not found or belongs to another tenant.")

        await db.delete(media)
        await db.commit()

        # Log to MongoDB
        await log_audit_event(
            action="MEDIA_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={"media_id": str(media_id)}
        )

        return True

media_service = MediaService()
