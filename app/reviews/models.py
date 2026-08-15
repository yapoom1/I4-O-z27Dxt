import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class ProductReview(Base):
    """SQLAlchemy model representing product reviews and ratings."""
    __tablename__ = "product_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating_points = Column(Integer, nullable=False)  # 1 to 5 scale
    review = Column(String, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships


class OrderReview(Base):
    """SQLAlchemy model representing order reviews and ratings."""
    __tablename__ = "order_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    rating_points = Column(Integer, nullable=False)  # 1 to 5 scale
    review = Column(String, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CompanyReview(Base):
    """SQLAlchemy model representing company/tenant reviews and ratings."""
    __tablename__ = "company_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    rating_points = Column(Integer, nullable=False)  # 1 to 5 scale
    review = Column(String, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
