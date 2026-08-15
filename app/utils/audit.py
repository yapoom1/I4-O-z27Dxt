import logging
from datetime import datetime
from typing import Any, Dict, Optional
from beanie import Document
from beanie.exceptions import CollectionWasNotInitialized
from pydantic import Field

logger = logging.getLogger(__name__)

class AuditLog(Document):
    """Beanie ODM Document model for audit logging."""
    tenant_id: Optional[str] = Field(default=None, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    action: str = Field(..., index=True)
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"


async def log_audit_event(
    action: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Helper function to log audit events to MongoDB, falling back to Python logging if down."""
    if details is None:
        details = {}
    try:
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            details=details
        )
        await audit.insert()
        logger.info(f"Audit Log Inserted: {action} for user={user_id}, tenant={tenant_id}")
    except CollectionWasNotInitialized:
        logger.warning(
            f"[Audit Fallback Log] {action} | Tenant: {tenant_id} | User: {user_id} | Details: {details}"
        )
    except Exception as e:
        logger.error(
            f"Failed to log audit event to MongoDB: {e}. Event: {action} | Details: {details}"
        )
