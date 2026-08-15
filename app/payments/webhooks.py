import uuid
import json
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.postgres import get_db_session
from app.payments.services import PaymentGatewayService
from app.payments.models import PaymentGateway, TenantPaymentGateway

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/payments", tags=["Payment Webhooks"])

@router.post("/platform/razorpay")
async def platform_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Webhook callback for platform routing (Gubera routed accounts)."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    if not signature:
        logger.warning("Missing x-razorpay-signature header in platform webhook.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature header."
        )

    # Fetch active platform payment gateway configuration
    stmt = select(PaymentGateway).where(PaymentGateway.is_active == True)
    res = await db.execute(stmt)
    platform_gw = res.scalar_one_or_none()
    
    if not platform_gw or not platform_gw.webhook_secret:
        logger.error("Platform payment gateway or webhook secret not configured/active.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform gateway webhooks not active."
        )

    # Verify signature
    is_valid = PaymentGatewayService.verify_signature(body, signature, platform_gw.webhook_secret)
    if not is_valid:
        logger.warning("Invalid webhook signature for platform payment callback.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature verification."
        )

    try:
        event_data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    processed = await PaymentGatewayService.process_webhook(db, event_data)
    if not processed:
        return {"status": "skipped", "message": "Event not processed"}
        
    return {"status": "processed"}


@router.post("/{tenant_id}/razorpay")
async def tenant_razorpay_webhook(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Webhook callback for direct tenant billing configuration."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    if not signature:
        logger.warning(f"Missing x-razorpay-signature header in tenant {tenant_id} webhook.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature header."
        )

    # Fetch active tenant payment gateway configuration
    stmt = select(TenantPaymentGateway).where(
        (TenantPaymentGateway.tenant_id == tenant_id) &
        (TenantPaymentGateway.is_active == True)
    )
    res = await db.execute(stmt)
    tenant_gw = res.scalar_one_or_none()
    
    if not tenant_gw or not tenant_gw.webhook_secret:
        logger.error(f"Tenant {tenant_id} payment gateway or webhook secret not configured/active.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant gateway webhooks not active."
        )

    # Verify signature
    is_valid = PaymentGatewayService.verify_signature(body, signature, tenant_gw.webhook_secret)
    if not is_valid:
        logger.warning(f"Invalid webhook signature for tenant {tenant_id} callback.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature verification."
        )

    try:
        event_data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    processed = await PaymentGatewayService.process_webhook(db, event_data)
    if not processed:
        return {"status": "skipped", "message": "Event not processed"}
        
    return {"status": "processed"}
