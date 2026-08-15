import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.subscriptions.models import (
    SubscriptionPlan,
    SubscriptionFeatures,
    TenantSubscription,
    TenantSubscriptionPayment,
)


# ---------------------------------------------------------------------------
# Subscription Plan Repository
# ---------------------------------------------------------------------------

class SubscriptionPlanRepository:
    """Pure data-access layer for SubscriptionPlan records."""

    @staticmethod
    async def create(
        db: AsyncSession,
        title: str,
        price: float,
        billing_cycle: str,
        type: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> SubscriptionPlan:
        plan = SubscriptionPlan(
            title=title,
            description=description,
            price=price,
            billing_cycle=billing_cycle,
            type=type,
            is_active=is_active,
        )
        db.add(plan)
        await db.flush()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def get_by_id(db: AsyncSession, plan_id: uuid.UUID) -> Optional[SubscriptionPlan]:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title(db: AsyncSession, title: str) -> Optional[SubscriptionPlan]:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.title == title)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        db: AsyncSession,
        active_only: bool = False,
    ) -> List[SubscriptionPlan]:
        stmt = select(SubscriptionPlan)
        if active_only:
            stmt = stmt.where(SubscriptionPlan.is_active == True)
        stmt = stmt.order_by(SubscriptionPlan.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        plan: SubscriptionPlan,
        **kwargs,
    ) -> SubscriptionPlan:
        for key, value in kwargs.items():
            setattr(plan, key, value)
        plan.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def delete(db: AsyncSession, plan: SubscriptionPlan) -> bool:
        await db.delete(plan)
        await db.flush()
        return True


# ---------------------------------------------------------------------------
# Subscription Features Repository
# ---------------------------------------------------------------------------

class SubscriptionFeaturesRepository:
    """Pure data-access layer for SubscriptionFeatures records (1:1 per plan)."""

    @staticmethod
    async def create(
        db: AsyncSession,
        plan_id: uuid.UUID,
        user_limit: Optional[int] = None,
        product_limit: Optional[int] = None,
        coupon_limit: Optional[int] = None,
        cod_enabled: bool = False,
        cms_enabled: bool = False,
        otp_login_enabled: bool = False,
        custom_domain_enabled: bool = False,
    ) -> SubscriptionFeatures:
        features = SubscriptionFeatures(
            plan_id=plan_id,
            user_limit=user_limit,
            product_limit=product_limit,
            coupon_limit=coupon_limit,
            cod_enabled=cod_enabled,
            cms_enabled=cms_enabled,
            otp_login_enabled=otp_login_enabled,
            custom_domain_enabled=custom_domain_enabled,
        )
        db.add(features)
        await db.flush()
        await db.refresh(features)
        return features

    @staticmethod
    async def get_by_plan_id(
        db: AsyncSession,
        plan_id: uuid.UUID,
    ) -> Optional[SubscriptionFeatures]:
        stmt = select(SubscriptionFeatures).where(SubscriptionFeatures.plan_id == plan_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        features: SubscriptionFeatures,
        **kwargs,
    ) -> SubscriptionFeatures:
        for key, value in kwargs.items():
            setattr(features, key, value)
        features.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(features)
        return features


# ---------------------------------------------------------------------------
# Tenant Subscription Repository
# ---------------------------------------------------------------------------

class TenantSubscriptionRepository:
    """Pure data-access layer for TenantSubscription records."""

    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        plan_title_snapshot: str,
        plan_price_snapshot: float,
        amount: float,
        start_date: datetime,
        end_date: datetime,
        status: str = "ACTIVE",
        coupon_id: Optional[uuid.UUID] = None,
        remark: Optional[str] = None,
    ) -> TenantSubscription:
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=plan_id,
            plan_title_snapshot=plan_title_snapshot,
            plan_price_snapshot=plan_price_snapshot,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            status=status,
            coupon_id=coupon_id,
            remark=remark,
        )
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        subscription_id: uuid.UUID,
    ) -> Optional[TenantSubscription]:
        stmt = select(TenantSubscription).where(TenantSubscription.id == subscription_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_by_tenant(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> Optional[TenantSubscription]:
        """Return the first subscription with status ACTIVE or TRIAL for the tenant."""
        stmt = (
            select(TenantSubscription)
            .where(
                (TenantSubscription.tenant_id == tenant_id)
                & (TenantSubscription.status.in_(["ACTIVE", "TRIAL"]))
            )
            .order_by(TenantSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_by_tenant(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> List[TenantSubscription]:
        stmt = (
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        subscription: TenantSubscription,
        **kwargs,
    ) -> TenantSubscription:
        for key, value in kwargs.items():
            setattr(subscription, key, value)
        subscription.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(subscription)
        return subscription


# ---------------------------------------------------------------------------
# Tenant Subscription Payment Repository
# ---------------------------------------------------------------------------

class TenantSubscriptionPaymentRepository:
    """Pure data-access layer for TenantSubscriptionPayment records."""

    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_subscription_id: uuid.UUID,
        amount: float,
        payment_method: str,
        status: str = "PENDING",
        transaction_id: Optional[str] = None,
        paid_at: Optional[datetime] = None,
    ) -> TenantSubscriptionPayment:
        payment = TenantSubscriptionPayment(
            tenant_subscription_id=tenant_subscription_id,
            amount=amount,
            payment_method=payment_method,
            status=status,
            transaction_id=transaction_id,
            paid_at=paid_at,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        payment_id: uuid.UUID,
    ) -> Optional[TenantSubscriptionPayment]:
        stmt = select(TenantSubscriptionPayment).where(
            TenantSubscriptionPayment.id == payment_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_subscription(
        db: AsyncSession,
        tenant_subscription_id: uuid.UUID,
    ) -> List[TenantSubscriptionPayment]:
        stmt = (
            select(TenantSubscriptionPayment)
            .where(
                TenantSubscriptionPayment.tenant_subscription_id == tenant_subscription_id
            )
            .order_by(TenantSubscriptionPayment.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
