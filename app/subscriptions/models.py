import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey,
    Boolean, Integer, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base


class SubscriptionPlan(Base):
    """SQLAlchemy model representing a subscription plan in the platform catalog."""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(String(20), nullable=False)  # MONTHLY | YEARLY
    type = Column(String(50), nullable=False)            # e.g. BASIC, PRO, ENTERPRISE
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    features = relationship(
        "SubscriptionFeatures",
        back_populates="plan",
        uselist=False,
        cascade="all, delete-orphan"
    )
    tenant_subscriptions = relationship(
        "TenantSubscription",
        back_populates="plan",
        cascade="all, delete-orphan"
    )


class SubscriptionFeatures(Base):
    """SQLAlchemy model for feature flags and limits tied to a subscription plan (1:1 with plan)."""
    __tablename__ = "subscription_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Integer limits
    user_limit = Column(Integer, nullable=True)        # NULL means unlimited
    product_limit = Column(Integer, nullable=True)     # NULL means unlimited
    coupon_limit = Column(Integer, nullable=True)      # NULL means unlimited

    # Feature flags
    cod_enabled = Column(Boolean, default=False, nullable=False)
    cms_enabled = Column(Boolean, default=False, nullable=False)
    otp_login_enabled = Column(Boolean, default=False, nullable=False)
    custom_domain_enabled = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    plan = relationship("SubscriptionPlan", back_populates="features")


class TenantSubscription(Base):
    """SQLAlchemy model tracking which subscription plan a tenant is currently on."""
    __tablename__ = "tenant_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Snapshots so historical records are immutable even if plan changes
    plan_title_snapshot = Column(String(100), nullable=False)
    plan_price_snapshot = Column(Numeric(10, 2), nullable=False)

    # Subscription lifecycle
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)
    # ACTIVE | EXPIRED | CANCELLED | TRIAL
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Billing
    coupon_id = Column(
        UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)  # Final amount after any coupon discount
    remark = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    plan = relationship("SubscriptionPlan", back_populates="tenant_subscriptions")
    coupon = relationship("Coupon")
    payments = relationship(
        "TenantSubscriptionPayment",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )


class TenantSubscriptionPayment(Base):
    """SQLAlchemy model for payment transactions linked to a tenant subscription."""
    __tablename__ = "tenant_subscription_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    amount = Column(Numeric(10, 2), nullable=False)
    transaction_id = Column(String(255), nullable=True, unique=True, index=True)
    payment_method = Column(String(50), nullable=False)  # e.g. CARD, UPI, BANK_TRANSFER
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    # PENDING | SUCCESS | FAILED | REFUNDED
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    subscription = relationship("TenantSubscription", back_populates="payments")
