import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.subscriptions.models import (
    SubscriptionPlan,
    SubscriptionFeatures,
    TenantSubscription,
    TenantSubscriptionPayment,
)
from app.subscriptions.repositories import (
    SubscriptionPlanRepository,
    SubscriptionFeaturesRepository,
    TenantSubscriptionRepository,
    TenantSubscriptionPaymentRepository,
)
from app.utils.exceptions import ValidationError, UnauthorizedError
from app.utils.audit import log_audit_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed values (kept as module-level constants for easy maintenance)
# ---------------------------------------------------------------------------

VALID_BILLING_CYCLES = {"MONTHLY", "YEARLY"}
VALID_SUBSCRIPTION_STATUSES = {"ACTIVE", "EXPIRED", "CANCELLED", "TRIAL"}
VALID_PAYMENT_STATUSES = {"PENDING", "SUCCESS", "FAILED", "REFUNDED"}


# ---------------------------------------------------------------------------
# Subscription Plan Service
# ---------------------------------------------------------------------------

class SubscriptionPlanService:
    """Business logic for managing subscription plan catalog."""

    @staticmethod
    async def create_plan(
        db: AsyncSession,
        title: str,
        price: float,
        billing_cycle: str,
        type: str,
        description: Optional[str] = None,
        is_active: bool = True,
        actor_user_id: Optional[str] = None,
    ) -> SubscriptionPlan:
        """Create a new subscription plan. Title must be unique."""
        billing_cycle = billing_cycle.upper()
        if billing_cycle not in VALID_BILLING_CYCLES:
            raise ValidationError(
                f"Invalid billing_cycle '{billing_cycle}'. Must be one of {VALID_BILLING_CYCLES}."
            )

        existing = await SubscriptionPlanRepository.get_by_title(db, title)
        if existing:
            raise ValidationError(f"Subscription plan with title '{title}' already exists.")

        if price < 0:
            raise ValidationError("Plan price cannot be negative.")

        plan = await SubscriptionPlanRepository.create(
            db=db,
            title=title,
            description=description,
            price=price,
            billing_cycle=billing_cycle,
            type=type,
            is_active=is_active,
        )
        await db.commit()
        await db.refresh(plan)

        await log_audit_event(
            action="SUBSCRIPTION_PLAN_CREATED",
            user_id=actor_user_id,
            details={"plan_id": str(plan.id), "title": plan.title},
        )
        return plan

    @staticmethod
    async def update_plan(
        db: AsyncSession,
        plan_id: uuid.UUID,
        actor_user_id: Optional[str] = None,
        **kwargs,
    ) -> SubscriptionPlan:
        """Update fields on an existing plan."""
        plan = await SubscriptionPlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValidationError("Subscription plan not found.")

        if "billing_cycle" in kwargs and kwargs["billing_cycle"]:
            kwargs["billing_cycle"] = kwargs["billing_cycle"].upper()
            if kwargs["billing_cycle"] not in VALID_BILLING_CYCLES:
                raise ValidationError(
                    f"Invalid billing_cycle. Must be one of {VALID_BILLING_CYCLES}."
                )

        if "price" in kwargs and kwargs["price"] is not None and kwargs["price"] < 0:
            raise ValidationError("Plan price cannot be negative.")

        # Check title uniqueness if changing
        if "title" in kwargs and kwargs["title"] and kwargs["title"] != plan.title:
            existing = await SubscriptionPlanRepository.get_by_title(db, kwargs["title"])
            if existing:
                raise ValidationError(
                    f"A subscription plan with title '{kwargs['title']}' already exists."
                )

        plan = await SubscriptionPlanRepository.update(db, plan, **kwargs)
        await db.commit()
        await db.refresh(plan)

        await log_audit_event(
            action="SUBSCRIPTION_PLAN_UPDATED",
            user_id=actor_user_id,
            details={"plan_id": str(plan_id), "fields": list(kwargs.keys())},
        )
        return plan

    @staticmethod
    async def delete_plan(
        db: AsyncSession,
        plan_id: uuid.UUID,
        actor_user_id: Optional[str] = None,
    ) -> bool:
        """Delete a plan. Raises ValidationError if any active subscriptions exist."""
        plan = await SubscriptionPlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValidationError("Subscription plan not found.")

        # Guard: do not delete plan with active subscriptions
        from sqlalchemy.future import select as sa_select
        from app.subscriptions.models import TenantSubscription as TSSub
        stmt = sa_select(TSSub).where(
            (TSSub.plan_id == plan_id) & (TSSub.status.in_(["ACTIVE", "TRIAL"]))
        )
        result = await db.execute(stmt)
        if result.scalars().first():
            raise ValidationError(
                "Cannot delete a plan with active or trial tenant subscriptions."
            )

        await SubscriptionPlanRepository.delete(db, plan)
        await db.commit()

        await log_audit_event(
            action="SUBSCRIPTION_PLAN_DELETED",
            user_id=actor_user_id,
            details={"plan_id": str(plan_id)},
        )
        return True

    @staticmethod
    async def get_plan_by_id(
        db: AsyncSession,
        plan_id: uuid.UUID,
    ) -> Optional[SubscriptionPlan]:
        return await SubscriptionPlanRepository.get_by_id(db, plan_id)

    @staticmethod
    async def get_all_plans(
        db: AsyncSession,
        active_only: bool = False,
    ) -> List[SubscriptionPlan]:
        return await SubscriptionPlanRepository.list_all(db, active_only=active_only)


# ---------------------------------------------------------------------------
# Subscription Features Service
# ---------------------------------------------------------------------------

class SubscriptionFeaturesService:
    """Business logic for managing feature configuration of a plan."""

    @staticmethod
    async def create_features(
        db: AsyncSession,
        plan_id: uuid.UUID,
        user_limit: Optional[int] = None,
        product_limit: Optional[int] = None,
        coupon_limit: Optional[int] = None,
        cod_enabled: bool = False,
        cms_enabled: bool = False,
        otp_login_enabled: bool = False,
        custom_domain_enabled: bool = False,
        actor_user_id: Optional[str] = None,
    ) -> SubscriptionFeatures:
        """Create features for a plan. Raises if features already exist."""
        plan = await SubscriptionPlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValidationError("Subscription plan not found.")

        existing = await SubscriptionFeaturesRepository.get_by_plan_id(db, plan_id)
        if existing:
            raise ValidationError(
                "Features already exist for this plan. Use updateSubscriptionFeatures to modify."
            )

        features = await SubscriptionFeaturesRepository.create(
            db=db,
            plan_id=plan_id,
            user_limit=user_limit,
            product_limit=product_limit,
            coupon_limit=coupon_limit,
            cod_enabled=cod_enabled,
            cms_enabled=cms_enabled,
            otp_login_enabled=otp_login_enabled,
            custom_domain_enabled=custom_domain_enabled,
        )
        await db.commit()
        await db.refresh(features)

        await log_audit_event(
            action="SUBSCRIPTION_FEATURES_CREATED",
            user_id=actor_user_id,
            details={"plan_id": str(plan_id), "features_id": str(features.id)},
        )
        return features

    @staticmethod
    async def update_features(
        db: AsyncSession,
        plan_id: uuid.UUID,
        actor_user_id: Optional[str] = None,
        **kwargs,
    ) -> SubscriptionFeatures:
        """Update feature configuration for a plan."""
        features = await SubscriptionFeaturesRepository.get_by_plan_id(db, plan_id)
        if not features:
            raise ValidationError(
                "No features found for this plan. Use createSubscriptionFeatures first."
            )

        features = await SubscriptionFeaturesRepository.update(db, features, **kwargs)
        await db.commit()
        await db.refresh(features)

        await log_audit_event(
            action="SUBSCRIPTION_FEATURES_UPDATED",
            user_id=actor_user_id,
            details={"plan_id": str(plan_id), "fields": list(kwargs.keys())},
        )
        return features

    @staticmethod
    async def get_features_by_plan(
        db: AsyncSession,
        plan_id: uuid.UUID,
    ) -> Optional[SubscriptionFeatures]:
        return await SubscriptionFeaturesRepository.get_by_plan_id(db, plan_id)


# ---------------------------------------------------------------------------
# Tenant Subscription Service
# ---------------------------------------------------------------------------

class TenantSubscriptionService:
    """Business logic for tenant subscriptions — enforces one-active rule and price snapshots."""

    @staticmethod
    async def subscribe_tenant(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        status: str = "ACTIVE",
        coupon_id: Optional[uuid.UUID] = None,
        remark: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> TenantSubscription:
        """
        Subscribe a tenant to a plan.

        Business rules:
        - Tenant must NOT already have an ACTIVE or TRIAL subscription.
        - price snapshot is taken from plan.price at subscription time.
        - If coupon_id is provided, validate it exists and compute discount.
        """
        status = status.upper()
        if status not in VALID_SUBSCRIPTION_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Must be one of {VALID_SUBSCRIPTION_STATUSES}."
            )

        # Enforce one-active rule
        existing_active = await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)
        if existing_active:
            raise ValidationError(
                "Tenant already has an active subscription. Cancel or expire it first."
            )

        # Fetch plan
        plan = await SubscriptionPlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValidationError("Subscription plan not found.")
        if not plan.is_active:
            raise ValidationError("Cannot subscribe to an inactive plan.")

        # Calculate amount
        amount = Decimal(str(plan.price))
        if coupon_id:
            amount = await TenantSubscriptionService._apply_coupon_discount(
                db, coupon_id, amount
            )

        if start_date >= end_date:
            raise ValidationError("start_date must be before end_date.")

        subscription = await TenantSubscriptionRepository.create(
            db=db,
            tenant_id=tenant_id,
            plan_id=plan_id,
            plan_title_snapshot=plan.title,
            plan_price_snapshot=float(plan.price),
            amount=float(amount),
            start_date=start_date,
            end_date=end_date,
            status=status,
            coupon_id=coupon_id,
            remark=remark,
        )
        await db.commit()
        await db.refresh(subscription)

        await log_audit_event(
            action="TENANT_SUBSCRIBED",
            tenant_id=str(tenant_id),
            user_id=actor_user_id,
            details={
                "subscription_id": str(subscription.id),
                "plan_id": str(plan_id),
                "plan_title": plan.title,
                "amount": float(amount),
            },
        )
        return subscription

    @staticmethod
    async def renew_subscription(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        coupon_id: Optional[uuid.UUID] = None,
        remark: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> TenantSubscription:
        """
        Renew a tenant subscription.

        This cancels any current active subscription and creates a new one.
        A fresh price snapshot is taken from the current plan price.
        """
        # Cancel existing active subscription if any
        existing_active = await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)
        if existing_active:
            await TenantSubscriptionRepository.update(
                db, existing_active, status="CANCELLED", remark="Cancelled due to renewal."
            )

        # Delegate to subscribe_tenant (which enforces all the rules)
        return await TenantSubscriptionService.subscribe_tenant(
            db=db,
            tenant_id=tenant_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
            status="ACTIVE",
            coupon_id=coupon_id,
            remark=remark,
            actor_user_id=actor_user_id,
        )

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        remark: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> TenantSubscription:
        """Cancel the active subscription for a tenant."""
        subscription = await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)
        if not subscription:
            raise ValidationError("No active subscription found for this tenant.")

        subscription = await TenantSubscriptionRepository.update(
            db, subscription, status="CANCELLED", remark=remark
        )
        await db.commit()
        await db.refresh(subscription)

        await log_audit_event(
            action="TENANT_SUBSCRIPTION_CANCELLED",
            tenant_id=str(tenant_id),
            user_id=actor_user_id,
            details={"subscription_id": str(subscription.id)},
        )
        return subscription

    # ------------------------------------------------------------------
    # Feature-resolution helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_active_subscription(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> Optional[TenantSubscription]:
        """Return the current ACTIVE or TRIAL subscription for a tenant."""
        return await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)

    @staticmethod
    async def is_subscription_active(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Return True if the tenant has a currently active subscription."""
        sub = await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)
        if not sub:
            return False
        now = datetime.utcnow()
        return sub.status in ("ACTIVE", "TRIAL") and sub.end_date > now

    @staticmethod
    async def get_subscription_features(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> Optional[SubscriptionFeatures]:
        """
        Resolve features through:
        tenant_subscription -> subscription_plan -> subscription_features
        """
        sub = await TenantSubscriptionRepository.get_active_by_tenant(db, tenant_id)
        if not sub:
            return None
        return await SubscriptionFeaturesRepository.get_by_plan_id(db, sub.plan_id)

    @staticmethod
    async def can_use_cms(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return bool(features and features.cms_enabled)

    @staticmethod
    async def can_use_cod(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return bool(features and features.cod_enabled)

    @staticmethod
    async def can_use_otp_login(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return bool(features and features.otp_login_enabled)

    @staticmethod
    async def get_user_limit(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[int]:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return features.user_limit if features else None

    @staticmethod
    async def get_product_limit(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[int]:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return features.product_limit if features else None

    @staticmethod
    async def get_coupon_limit(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[int]:
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return features.coupon_limit if features else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _apply_coupon_discount(
        db: AsyncSession,
        coupon_id: uuid.UUID,
        base_amount: Decimal,
    ) -> Decimal:
        """Validate coupon and return discounted amount. Raises on invalid coupon."""
        from sqlalchemy.future import select as sa_select
        from app.promotions.models import Coupon

        stmt = sa_select(Coupon).where(Coupon.id == coupon_id)
        result = await db.execute(stmt)
        coupon = result.scalar_one_or_none()

        if not coupon:
            raise ValidationError(f"Coupon with id '{coupon_id}' not found.")
        if not coupon.is_active:
            raise ValidationError("The provided coupon is not active.")

        now = datetime.utcnow()
        if now < coupon.start_date or now > coupon.end_date:
            raise ValidationError("The provided coupon is not valid at this time.")

        discount_type = coupon.discount_type.upper()
        discount_value = Decimal(str(coupon.discount_value))

        if discount_type == "PERCENTAGE":
            discount = (base_amount * discount_value / Decimal("100")).quantize(Decimal("0.01"))
            if coupon.max_discount_amount:
                discount = min(discount, Decimal(str(coupon.max_discount_amount)))
        elif discount_type == "FLAT":
            discount = discount_value
        else:
            discount = Decimal("0.00")

        return max(Decimal("0.00"), base_amount - discount)


# ---------------------------------------------------------------------------
# Tenant Subscription Payment Service
# ---------------------------------------------------------------------------

class TenantSubscriptionPaymentService:
    """Business logic for subscription payment transactions."""

    @staticmethod
    async def create_payment(
        db: AsyncSession,
        tenant_subscription_id: uuid.UUID,
        amount: float,
        payment_method: str,
        status: str = "PENDING",
        transaction_id: Optional[str] = None,
        paid_at: Optional[datetime] = None,
        actor_user_id: Optional[str] = None,
    ) -> TenantSubscriptionPayment:
        """Record a payment for a subscription."""
        status = status.upper()
        if status not in VALID_PAYMENT_STATUSES:
            raise ValidationError(
                f"Invalid payment status '{status}'. Must be one of {VALID_PAYMENT_STATUSES}."
            )

        # Verify subscription exists
        sub = await TenantSubscriptionRepository.get_by_id(db, tenant_subscription_id)
        if not sub:
            raise ValidationError("Tenant subscription not found.")

        # If SUCCESS, set paid_at automatically
        if status == "SUCCESS" and paid_at is None:
            paid_at = datetime.utcnow()

        payment = await TenantSubscriptionPaymentRepository.create(
            db=db,
            tenant_subscription_id=tenant_subscription_id,
            amount=amount,
            payment_method=payment_method,
            status=status,
            transaction_id=transaction_id,
            paid_at=paid_at,
        )
        await db.commit()
        await db.refresh(payment)

        await log_audit_event(
            action="SUBSCRIPTION_PAYMENT_CREATED",
            user_id=actor_user_id,
            details={
                "payment_id": str(payment.id),
                "subscription_id": str(tenant_subscription_id),
                "amount": amount,
                "status": status,
            },
        )
        return payment

    @staticmethod
    async def get_payments_by_subscription(
        db: AsyncSession,
        tenant_subscription_id: uuid.UUID,
    ) -> List[TenantSubscriptionPayment]:
        return await TenantSubscriptionPaymentRepository.list_by_subscription(
            db, tenant_subscription_id
        )


# ---------------------------------------------------------------------------
# Module-level singletons (following existing pattern)
# ---------------------------------------------------------------------------

subscription_plan_service = SubscriptionPlanService()
subscription_features_service = SubscriptionFeaturesService()
tenant_subscription_service = TenantSubscriptionService()
tenant_subscription_payment_service = TenantSubscriptionPaymentService()
