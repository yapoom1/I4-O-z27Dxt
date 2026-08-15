import uuid
from typing import Optional
from datetime import datetime
from pydantic import Field
from beanie import Document, Indexed

class Category(Document):
    """Beanie document representing a Category in the multi-tenant system."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    tenant_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    description_long: Optional[str] = None
    sku: Optional[str] = None
    thumbnail_media_id: Optional[uuid.UUID] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"
        indexes = [
            [("tenant_id", 1), ("sku", 1)]
        ]
