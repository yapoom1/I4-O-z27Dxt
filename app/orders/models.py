import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delivery_address_id = Column(UUID(as_uuid=True), ForeignKey("user_addresses.id", ondelete="SET NULL"), nullable=True)
    
    delivery_service = Column(String, nullable=True)
    delivery_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    estimated_days = Column(Integer, nullable=True)
    
    item_total = Column(Numeric(10, 2), nullable=False)
    discount_applied = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax = Column(Numeric(10, 2), default=0.00, nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    
    order_status = Column(String, default="PENDING", nullable=False, index=True)
    payment_status = Column(String, default="UNPAID", nullable=False, index=True)
    
    applied_coupons = Column(JSONB, default=list, nullable=False)
    shipping_metadata = Column(JSONB, default=dict, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    returns = relationship("OrderReturn", back_populates="order", cascade="all, delete-orphan")
    address = relationship("UserAddress")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_applied = Column(Numeric(10, 2), default=0.00, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")


class OrderPayment(Base):
    __tablename__ = "order_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String, nullable=False)  # e.g., CARD, COD, UPI, WALLET
    status = Column(String, default="PENDING", nullable=False, index=True)  # PENDING, COMPLETED, FAILED, REFUNDED
    
    transaction_reference = Column(String, nullable=True, index=True)
    gateway = Column(String, nullable=True, index=True)  # e.g., RAZORPAY, GUBERA
    gateway_response = Column(JSONB, default=dict, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="payments")


class OrderReturn(Base):
    __tablename__ = "order_returns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING_APPROVAL", nullable=False, index=True)  # PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED
    refund_status = Column(String, default="PENDING", nullable=False, index=True)  # PENDING, REFUNDED, NO_REFUND
    refund_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="returns")
    items = relationship("OrderReturnItem", back_populates="order_return", cascade="all, delete-orphan")


class OrderReturnItem(Base):
    __tablename__ = "order_return_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_return_id = Column(UUID(as_uuid=True), ForeignKey("order_returns.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    condition = Column(String, nullable=False)  # UNOPENED, DAMAGED, DEFECTIVE
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order_return = relationship("OrderReturn", back_populates="items")
    order_item = relationship("OrderItem")
