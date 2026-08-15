import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class UserReferral(Base):
    """SQLAlchemy model representing user referral details and code."""
    __tablename__ = "user_referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    referral_points = Column(Numeric(12, 2), default=0.00, nullable=False)
    referral_code = Column(String, nullable=False, unique=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="referral")


class UserReferralHistory(Base):
    """SQLAlchemy model representing records of successful user referrals."""
    __tablename__ = "user_referral_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referral_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True) # referred user
    referrer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True) # referrer
    referred_entity = Column(String, nullable=False)  # USER, PRODUCT, ORDER
    referred_entity_id = Column(UUID(as_uuid=True), nullable=True)
    points = Column(Numeric(12, 2), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserReferralPointsTransactionHistory(Base):
    """SQLAlchemy model representing ledger transactions specifically for referral points."""
    __tablename__ = "user_referral_points_transaction_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_referral_id = Column(UUID(as_uuid=True), ForeignKey("user_referrals.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("user_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    points = Column(Numeric(12, 2), nullable=False)
    type = Column(String, nullable=False)  # CREDIT or DEBIT
    payment_id = Column(UUID(as_uuid=True), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
