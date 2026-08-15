import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Category(Base):
    """SQLAlchemy model representing a Category in the multi-tenant system."""
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True)
    
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(String, nullable=True)
    description_long = Column(String, nullable=True)
    sku = Column(String, nullable=True, index=True)
    thumbnail_media_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    products = relationship("Product", secondary="product_categories", back_populates="categories")

    # Constraints: enforce unique SKU *per tenant*
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_tenant_category_sku"),
    )


class ProductCategory(Base):
    """SQLAlchemy join table mapping Products to Categories (Many-to-Many)."""
    __tablename__ = "product_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints: prevent duplicate mapping
    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_category"),
    )
