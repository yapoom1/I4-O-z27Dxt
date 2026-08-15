import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Media(Base):
    """SQLAlchemy model representing a Media file in the multi-tenant system."""
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Generic entity binding (polymorphic)
    entity_name = Column(String, nullable=True, index=True)  # e.g., "product", "user"
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    file_path = Column(String, nullable=False)
    media_url = Column(String, nullable=False)
    media_type = Column(String, default="IMAGE", nullable=False)  # IMAGE, VIDEO, PDF, AUDIO, OTHER
    file_extension = Column(String, nullable=True)  # e.g., "jpg", "mp4", "pdf"
    alt_text = Column(String, nullable=True)
    meta_attributes = Column(JSONB, nullable=True)  # Flexible attributes (size, width, height, quality, duration etc.)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
