import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from beanie import Document
from pydantic import BaseModel, Field

class HomepageSection(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: str  # "banner", "products", "categories", "promo"
    title: str
    order: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)

class HomepageConfig(Document):
    tenant_id: uuid.UUID = Field(..., index=True, unique=True)
    version: int = 1
    status: str = "draft"  # "draft" or "published"
    sections: List[HomepageSection] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "homepage_configs"

# --- API Request Schemas ---

class CreateOrUpdateHomepageConfigRequest(BaseModel):
    status: str
    sections: List[HomepageSection]

class UpdateHomepageConfigRequest(BaseModel):
    status: Optional[str] = None
    sections: Optional[List[HomepageSection]] = None
