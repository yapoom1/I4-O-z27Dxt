import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class PaymentGateway(Base):
    """SQLAlchemy model representing payment gateways supported at system/platform level."""
    __tablename__ = "payment_gateways"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # e.g., RAZORPAY, STRIPE
    credentials = Column(JSONB, default=dict, nullable=False)  # Platform-level API keys/secrets
    webhook_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)  # Active platform gateway status
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TenantPaymentGateway(Base):
    """SQLAlchemy model representing payment gateway configuration for a specific tenant."""
    __tablename__ = "tenant_payment_gateways"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway_id = Column(UUID(as_uuid=True), ForeignKey("payment_gateways.id", ondelete="CASCADE"), nullable=False, index=True)
    credentials = Column(JSONB, default=dict, nullable=False)  # Tenant-level API keys/secrets
    webhook_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)  # Active tenant gateway status
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    gateway = relationship("PaymentGateway")

    __table_args__ = (
        UniqueConstraint("tenant_id", "gateway_id", name="uq_tenant_gateway"),
    )


class TenantCommission(Base):
    """SQLAlchemy model storing commission percentages and routing accounts for tenants using platform gateway."""
    __tablename__ = "tenant_commissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    commission_percent = Column(Numeric(5, 2), default=5.00, nullable=False)  # e.g., 5.00%
    linked_account_id = Column(String, nullable=False)  # Razorpay Account ID for Route/Transfer API
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")


class PendingCartPayment(Base):
    """SQLAlchemy model representing a pending payment checkout session before order creation."""
    __tablename__ = "pending_cart_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    gateway_order_id = Column(String, nullable=False, unique=True, index=True)  # Razorpay Order ID
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Store pricing constraints and cart items snapshot
    cart_items = Column(JSONB, default=list, nullable=False)
    billing_details = Column(JSONB, default=dict, nullable=False)
    
    status = Column(String, default="PENDING", nullable=False, index=True)  # PENDING, COMPLETED, FAILED
    gateway = Column(String, nullable=False)  # RAZORPAY, GUBERA
    gateway_response = Column(JSONB, default=dict, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    user = relationship("User", foreign_keys=[user_id])
