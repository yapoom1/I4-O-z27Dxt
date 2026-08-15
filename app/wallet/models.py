import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.postgres import Base

class UserWallet(Base):
    """SQLAlchemy model representing a user's loyalty/points wallet."""
    __tablename__ = "user_wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    points = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallet")


class UserWalletTransaction(Base):
    """SQLAlchemy model representing ledger entries for user wallets."""
    __tablename__ = "user_wallet_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("user_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    points = Column(Numeric(12, 2), nullable=False)
    type = Column(String, nullable=False)  # CREDIT or DEBIT
    payment_id = Column(UUID(as_uuid=True), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
