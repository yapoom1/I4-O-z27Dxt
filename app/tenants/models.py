import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Tenant(Base):
    """SQLAlchemy model representing a Tenant."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name = Column(String, unique=True, nullable=False, index=True)
    allow_multiple_coupons = Column(Boolean, default=False, nullable=False)
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    secondary_color = Column(String, nullable=True)
    theme_name = Column(String, nullable=True)
    
    # General Settings
    contact_telephone = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    support_email = Column(String, nullable=True)
    gstin_code = Column(String, nullable=True)
    currency = Column(String, default="INR", nullable=False)
    
    # Shiprocket Config
    shiprocket_email = Column(String, nullable=True)
    shiprocket_password = Column(String, nullable=True)
    shiprocket_token = Column(String, nullable=True)
    shiprocket_token_expires = Column(DateTime, nullable=True)

    # API Webhooks / Payment Keys
    payment_public_key = Column(String, nullable=True)
    payment_secret_key = Column(String, nullable=True)
    payment_sandbox_mode = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    domains = relationship("TenantDomain", back_populates="tenant", cascade="all, delete-orphan")


class TenantDomain(Base):
    """SQLAlchemy model representing a Custom Domain mapped to a Tenant."""
    __tablename__ = "tenant_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="domains")


class SystemDomain(Base):
    """SQLAlchemy model representing domains configured as system-level domains."""
    __tablename__ = "system_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
