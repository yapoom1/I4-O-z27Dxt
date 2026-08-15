import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Boolean, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class User(Base):
    """SQLAlchemy model representing a User."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    mobilenumber = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    password = Column(String, nullable=True)  # Hashed password (can be null if logged in via OTP only)
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, SUSPENDED
    role = Column(String, default="USER", nullable=False)  # SUPER_ADMIN, TENANT_ADMIN, USER
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")
    cart = relationship("UserCart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    wallet = relationship("UserWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    referral = relationship("UserReferral", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Constraints: enforce unique email and mobile number *per tenant*
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
        UniqueConstraint("tenant_id", "mobilenumber", name="uq_tenant_user_mobilenumber"),
    )


class UserAddress(Base):
    """SQLAlchemy model representing a User's Address."""
    __tablename__ = "user_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String, nullable=True)
    landmark = Column(String, nullable=True)
    pincode = Column(String, nullable=False)
    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
    customer_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    lat_long = Column(String, nullable=True)
    third_party_app_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="addresses")


class UserCart(Base):
    """SQLAlchemy model representing a User's Shopping Cart."""
    __tablename__ = "user_carts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    applied_coupons = Column(JSONB, default=list, nullable=False)
    delivery_fee = Column(Numeric(10, 2), nullable=True)
    delivery_service = Column(String, nullable=True)
    estimated_days = Column(Integer, nullable=True)
    delivery_address_id = Column(UUID(as_uuid=True), ForeignKey("user_addresses.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """SQLAlchemy model representing a line item in a shopping cart."""
    __tablename__ = "cart_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("user_carts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    cart = relationship("UserCart", back_populates="items")
    user = relationship("User")

    # Constraints: prevent duplicate product in same cart
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )



