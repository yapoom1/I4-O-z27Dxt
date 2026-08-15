import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.database.postgres import Base

class DeliveryRule(Base):
    __tablename__ = "delivery_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    field = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    value = Column(String, nullable=False)
    carrier = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DeliveryAgent(Base):
    __tablename__ = "delivery_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    zone = Column(String, nullable=False)
    active_orders = Column(Integer, default=0, nullable=False)
    status = Column(String, default="offline", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
