import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Product(Base):
    """SQLAlchemy model representing a Product in the multi-tenant system."""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(String, nullable=True)
    description_long = Column(String, nullable=True)
    sku = Column(String, nullable=True, index=True)
    product_type = Column(String, default="GOODS", nullable=False)  # GOODS, SERVICE, OTHERS
    thumbnail_media_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    parent = relationship("Product", remote_side=[id], back_populates="children")
    children = relationship("Product", back_populates="parent", cascade="all, delete-orphan")
    categories = relationship("Category", secondary="product_categories", back_populates="products")
    attributes = relationship("ProductAttributeValue", back_populates="product", cascade="all, delete-orphan")
    groups = relationship("ProductGroupLink", back_populates="product", cascade="all, delete-orphan")
    stock = relationship("ProductStock", back_populates="product", uselist=False, cascade="all, delete-orphan")
    shipping = relationship("ProductShipping", back_populates="product", uselist=False, cascade="all, delete-orphan")

    # Constraints: enforce unique SKU *per tenant*
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_tenant_product_sku"),
    )


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints: unique attribute name per tenant (e.g., only one 'color')
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_attribute_name"),
    )

    # Relationships
    values = relationship("AttributeValue", back_populates="attribute", cascade="all, delete-orphan")


class AttributeValue(Base):
    __tablename__ = "attribute_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attribute_id = Column(UUID(as_uuid=True), ForeignKey("attributes.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(String, nullable=False)
    hex_code = Column(String, nullable=True)  # Optional for color picker visual support
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints: unique value option per attribute (e.g., only one 'Red' under 'Color')
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_attribute_value"),
    )

    # Relationships
    attribute = relationship("Attribute", back_populates="values")


class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_value_id = Column(UUID(as_uuid=True), ForeignKey("attribute_values.id", ondelete="CASCADE"), nullable=False, index=True)
    
    pricing_type_id = Column(UUID(as_uuid=True), ForeignKey("pricing_types.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints: ensure value is not linked to the same product twice
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_value_id", name="uq_product_attribute_value_link"),
    )

    # Relationships
    product = relationship("Product", back_populates="attributes")
    attribute_value = relationship("AttributeValue")
    pricing_type = relationship("PricingType")


class ProductGroup(Base):
    """SQLAlchemy model representing a Product Group in the multi-tenant system."""
    __tablename__ = "product_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints: unique group name per tenant
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_product_group_name"),
    )

    # Relationships
    links = relationship("ProductGroupLink", back_populates="group", cascade="all, delete-orphan")


class ProductGroupLink(Base):
    """SQLAlchemy join table mapping Products to Product Groups."""
    __tablename__ = "product_group_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("product_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints: prevent duplicate mapping
    __table_args__ = (
        UniqueConstraint("product_id", "group_id", name="uq_product_group_link"),
    )

    # Relationships
    product = relationship("Product", back_populates="groups")
    group = relationship("ProductGroup", back_populates="links")


class ProductStock(Base):
    """SQLAlchemy model representing the inventory level of a Product per tenant."""
    __tablename__ = "product_stocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    stock = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="stock")

    # Constraints: ensure one stock record per product-tenant mapping
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", name="uq_tenant_product_stock"),
    )

class ProductShipping(Base):
    """SQLAlchemy model representing shipping dimensions for a product."""
    __tablename__ = "product_shipping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    weight = Column(Float, default=0.5, nullable=False) # Weight in kg
    length = Column(Float, default=10.0, nullable=False) # Length in cm
    width = Column(Float, default=10.0, nullable=False) # Width in cm
    height = Column(Float, default=10.0, nullable=False) # Height in cm

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="shipping")
