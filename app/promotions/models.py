import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Boolean, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Coupon(Base):
    """SQLAlchemy model representing a promotional coupon code in the multi-tenant system."""
    __tablename__ = "coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    code = Column(String(50), nullable=False, index=True)  # Normalized to uppercase on write
    description = Column(String, nullable=True)
    
    discount_type = Column(String, nullable=False)  # FLAT, PERCENTAGE, FREE_SHIPPING
    discount_value = Column(Numeric(10, 2), nullable=False)  # flat discount amount or percentage percentage
    
    min_order_value = Column(Numeric(10, 2), default=0.00, nullable=False)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)  # Cap for percentage discount
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    usage_limit_total = Column(Integer, nullable=True)  # Total coupon redemptions allowed
    usage_limit_per_user = Column(Integer, default=1, nullable=False)  # Allowed redemptions per user
    usage_count = Column(Integer, default=0, nullable=False)  # Cached redemptions counter
    
    is_active = Column(Boolean, default=True, nullable=False)
    rules = Column(JSONB, default=dict, nullable=False)  # Futuristic JSONB rule attributes
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")

    # Constraints: enforce unique coupon code *per tenant*
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tenant_coupon_code"),
    )


class CouponUsage(Base):
    """SQLAlchemy model serving as an immutable log/ledger of coupon redemptions."""
    __tablename__ = "coupon_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Scoped order identifier
    
    discount_applied = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    tenant = relationship("Tenant")
    coupon = relationship("Coupon")
    user = relationship("User")
