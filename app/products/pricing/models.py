import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class PricingType(Base):
    """SQLAlchemy model representing pricing classifications (e.g., selling_price, cost)."""
    __tablename__ = "pricing_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")

    # Constraints: enforce unique type name *per tenant*
    __table_args__ = (
        UniqueConstraint("tenant_id", "type", name="uq_tenant_pricing_type"),
    )


class ProductPrice(Base):
    """SQLAlchemy model representing the actual price mapping for a Product and PricingType."""
    __tablename__ = "product_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # product_id refers to MongoDB Product ID; no foreign key to Postgres products table
    product_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pricing_type_id = Column(UUID(as_uuid=True), ForeignKey("pricing_types.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    pricing_type = relationship("PricingType")

    # Constraints: enforce one price per product and pricing type combination
    __table_args__ = (
        UniqueConstraint("product_id", "pricing_type_id", name="uq_product_pricing_type_price"),
    )


class ProductPricingRule(Base):
    """SQLAlchemy model representing dynamic pricing rules and modifiers."""
    __tablename__ = "product_pricing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    # product_id refers to MongoDB Product ID; no foreign key to Postgres products table
    product_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    
    rule_type = Column(String, nullable=False)  # OVERRIDE, DISCOUNT_PERCENT, DISCOUNT_FIXED, MARKUP_PERCENT, MARKUP_FIXED
    value = Column(Numeric(10, 2), nullable=False)

    # Condition: Quantity
    min_quantity = Column(Integer, nullable=True)
    max_quantity = Column(Integer, nullable=True)

    # Condition: Location
    location_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    pincode = Column(String, nullable=True, index=True)

    # Condition: Time
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    start_hour = Column(Integer, nullable=True)
    end_hour = Column(Integer, nullable=True)

    # Condition: Stock
    min_stock = Column(Integer, nullable=True)
    max_stock = Column(Integer, nullable=True)

    pricing_type_id = Column(UUID(as_uuid=True), ForeignKey("pricing_types.id", ondelete="CASCADE"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    pricing_type = relationship("PricingType")
