import uuid
from datetime import datetime
from typing import Optional, List
import strawberry

from app.subscriptions.models import (
    SubscriptionPlan as DBSubscriptionPlan,
    SubscriptionFeatures as DBSubscriptionFeatures,
    TenantSubscription as DBTenantSubscription,
    TenantSubscriptionPayment as DBTenantSubscriptionPayment,
)
from app.subscriptions.services import (
    SubscriptionPlanService,
    SubscriptionFeaturesService,
    TenantSubscriptionService,
    TenantSubscriptionPaymentService,
)
from app.utils.exceptions import UnauthorizedError, ValidationError


# ===========================================================================
# GraphQL Output Types
# ===========================================================================

@strawberry.type
class SubscriptionFeaturesType:
    """GraphQL representation of subscription plan feature flags and limits."""
    id: uuid.UUID
    plan_id: uuid.UUID = strawberry.field(name="planId")
    user_limit: Optional[int] = strawberry.field(name="userLimit")
    product_limit: Optional[int] = strawberry.field(name="productLimit")
    coupon_limit: Optional[int] = strawberry.field(name="couponLimit")
    cod_enabled: bool = strawberry.field(name="codEnabled")
    cms_enabled: bool = strawberry.field(name="cmsEnabled")
    otp_login_enabled: bool = strawberry.field(name="otpLoginEnabled")
    custom_domain_enabled: bool = strawberry.field(name="customDomainEnabled")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    def __init__(self, db_features: DBSubscriptionFeatures):
        self.id = db_features.id
        self.plan_id = db_features.plan_id
        self.user_limit = db_features.user_limit
        self.product_limit = db_features.product_limit
        self.coupon_limit = db_features.coupon_limit
        self.cod_enabled = db_features.cod_enabled
        self.cms_enabled = db_features.cms_enabled
        self.otp_login_enabled = db_features.otp_login_enabled
        self.custom_domain_enabled = db_features.custom_domain_enabled
        self.created_at = db_features.created_at
        self.updated_at = db_features.updated_at


@strawberry.type
class SubscriptionPlanType:
    """GraphQL representation of a subscription plan."""
    id: uuid.UUID
    title: str
    description: Optional[str]
    price: float
    billing_cycle: str = strawberry.field(name="billingCycle")
    type: str
    is_active: bool = strawberry.field(name="isActive")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field(name="features")
    async def features(self, info: strawberry.Info) -> Optional[SubscriptionFeaturesType]:
        """Resolve the 1:1 features record for this plan."""
        db = info.context.db
        db_features = await SubscriptionFeaturesService.get_features_by_plan(db, self.id)
        return SubscriptionFeaturesType(db_features) if db_features else None

    def __init__(self, db_plan: DBSubscriptionPlan):
        self.id = db_plan.id
        self.title = db_plan.title
        self.description = db_plan.description
        self.price = float(db_plan.price)
        self.billing_cycle = db_plan.billing_cycle
        self.type = db_plan.type
        self.is_active = db_plan.is_active
        self.created_at = db_plan.created_at
        self.updated_at = db_plan.updated_at


@strawberry.type
class TenantSubscriptionPaymentType:
    """GraphQL representation of a subscription payment transaction."""
    id: uuid.UUID
    tenant_subscription_id: uuid.UUID = strawberry.field(name="tenantSubscriptionId")
    amount: float
    transaction_id: Optional[str] = strawberry.field(name="transactionId")
    payment_method: str = strawberry.field(name="paymentMethod")
    status: str
    paid_at: Optional[datetime] = strawberry.field(name="paidAt")
    created_at: datetime = strawberry.field(name="createdAt")

    def __init__(self, db_payment: DBTenantSubscriptionPayment):
        self.id = db_payment.id
        self.tenant_subscription_id = db_payment.tenant_subscription_id
        self.amount = float(db_payment.amount)
        self.transaction_id = db_payment.transaction_id
        self.payment_method = db_payment.payment_method
        self.status = db_payment.status
        self.paid_at = db_payment.paid_at
        self.created_at = db_payment.created_at


@strawberry.type
class TenantSubscriptionType:
    """GraphQL representation of a tenant's subscription record."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    plan_id: uuid.UUID = strawberry.field(name="planId")
    plan_title_snapshot: str = strawberry.field(name="planTitleSnapshot")
    plan_price_snapshot: float = strawberry.field(name="planPriceSnapshot")
    status: str
    start_date: datetime = strawberry.field(name="startDate")
    end_date: datetime = strawberry.field(name="endDate")
    coupon_id: Optional[uuid.UUID] = strawberry.field(name="couponId")
    amount: float
    remark: Optional[str]
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field(name="plan")
    async def plan(self, info: strawberry.Info) -> Optional[SubscriptionPlanType]:
        """Resolve the subscription plan details."""
        db = info.context.db
        db_plan = await SubscriptionPlanService.get_plan_by_id(db, self.plan_id)
        return SubscriptionPlanType(db_plan) if db_plan else None

    @strawberry.field(name="features")
    async def features(self, info: strawberry.Info) -> Optional[SubscriptionFeaturesType]:
        """Resolve features through: subscription -> plan -> features."""
        db = info.context.db
        db_features = await SubscriptionFeaturesService.get_features_by_plan(db, self.plan_id)
        return SubscriptionFeaturesType(db_features) if db_features else None

    @strawberry.field(name="payments")
    async def payments(self, info: strawberry.Info) -> List[TenantSubscriptionPaymentType]:
        """Resolve all payment records for this subscription."""
        db = info.context.db
        db_payments = await TenantSubscriptionPaymentService.get_payments_by_subscription(
            db, self.id
        )
        return [TenantSubscriptionPaymentType(p) for p in db_payments]

    def __init__(self, db_sub: DBTenantSubscription):
        self.id = db_sub.id
        self.tenant_id = db_sub.tenant_id
        self.plan_id = db_sub.plan_id
        self.plan_title_snapshot = db_sub.plan_title_snapshot
        self.plan_price_snapshot = float(db_sub.plan_price_snapshot)
        self.status = db_sub.status
        self.start_date = db_sub.start_date
        self.end_date = db_sub.end_date
        self.coupon_id = db_sub.coupon_id
        self.amount = float(db_sub.amount)
        self.remark = db_sub.remark
        self.created_at = db_sub.created_at
        self.updated_at = db_sub.updated_at


# ===========================================================================
# Input Types
# ===========================================================================

@strawberry.input
class CreateSubscriptionPlanInput:
    title: str
    price: float
    billing_cycle: str = strawberry.field(name="billingCycle")   # MONTHLY | YEARLY
    type: str
    description: Optional[str] = None
    is_active: Optional[bool] = strawberry.field(default=None, name="isActive")


@strawberry.input
class UpdateSubscriptionPlanInput:
    title: Optional[str] = None
    price: Optional[float] = None
    billing_cycle: Optional[str] = strawberry.field(default=None, name="billingCycle")
    type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = strawberry.field(default=None, name="isActive")


@strawberry.input
class CreateSubscriptionFeaturesInput:
    plan_id: uuid.UUID = strawberry.field(name="planId")
    user_limit: Optional[int] = strawberry.field(default=None, name="userLimit")
    product_limit: Optional[int] = strawberry.field(default=None, name="productLimit")
    coupon_limit: Optional[int] = strawberry.field(default=None, name="couponLimit")
    cod_enabled: Optional[bool] = strawberry.field(default=None, name="codEnabled")
    cms_enabled: Optional[bool] = strawberry.field(default=None, name="cmsEnabled")
    otp_login_enabled: Optional[bool] = strawberry.field(default=None, name="otpLoginEnabled")
    custom_domain_enabled: Optional[bool] = strawberry.field(default=None, name="customDomainEnabled")


@strawberry.input
class UpdateSubscriptionFeaturesInput:
    user_limit: Optional[int] = strawberry.field(default=None, name="userLimit")
    product_limit: Optional[int] = strawberry.field(default=None, name="productLimit")
    coupon_limit: Optional[int] = strawberry.field(default=None, name="couponLimit")
    cod_enabled: Optional[bool] = strawberry.field(default=None, name="codEnabled")
    cms_enabled: Optional[bool] = strawberry.field(default=None, name="cmsEnabled")
    otp_login_enabled: Optional[bool] = strawberry.field(default=None, name="otpLoginEnabled")
    custom_domain_enabled: Optional[bool] = strawberry.field(default=None, name="customDomainEnabled")


@strawberry.input
class SubscribeTenantInput:
    plan_id: uuid.UUID = strawberry.field(name="planId")
    start_date: datetime = strawberry.field(name="startDate")
    end_date: datetime = strawberry.field(name="endDate")
    status: Optional[str] = None
    coupon_id: Optional[uuid.UUID] = strawberry.field(default=None, name="couponId")
    remark: Optional[str] = None


@strawberry.input
class RenewTenantSubscriptionInput:
    plan_id: uuid.UUID = strawberry.field(name="planId")
    start_date: datetime = strawberry.field(name="startDate")
    end_date: datetime = strawberry.field(name="endDate")
    coupon_id: Optional[uuid.UUID] = strawberry.field(default=None, name="couponId")
    remark: Optional[str] = None


@strawberry.input
class CreateTenantSubscriptionPaymentInput:
    tenant_subscription_id: uuid.UUID = strawberry.field(name="tenantSubscriptionId")
    amount: float
    payment_method: str = strawberry.field(name="paymentMethod")
    status: Optional[str] = None
    transaction_id: Optional[str] = strawberry.field(default=None, name="transactionId")
    paid_at: Optional[datetime] = strawberry.field(default=None, name="paidAt")


# ===========================================================================
# Queries
# ===========================================================================

@strawberry.type
class SubscriptionQuery:

    @strawberry.field(name="getSubscriptionPlans")
    async def get_subscription_plans(
        self,
        info: strawberry.Info,
        active_only: Optional[bool] = strawberry.field(default=None, name="activeOnly"),
    ) -> List[SubscriptionPlanType]:
        """Fetch all subscription plans. Pass activeOnly=true to filter inactive plans."""
        db = info.context.db
        plans = await SubscriptionPlanService.get_all_plans(db, active_only=bool(active_only))
        return [SubscriptionPlanType(p) for p in plans]

    @strawberry.field(name="getSubscriptionPlanById")
    async def get_subscription_plan_by_id(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
    ) -> Optional[SubscriptionPlanType]:
        """Fetch a single subscription plan by ID."""
        db = info.context.db
        plan = await SubscriptionPlanService.get_plan_by_id(db, id)
        return SubscriptionPlanType(plan) if plan else None

    @strawberry.field(name="getTenantSubscription")
    async def get_tenant_subscription(
        self,
        info: strawberry.Info,
    ) -> Optional[TenantSubscriptionType]:
        """Fetch the active subscription for the current tenant context."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant context missing. Provide X-Tenant-ID header.")
        db = info.context.db
        sub = await TenantSubscriptionService.get_active_subscription(db, tenant_id)
        return TenantSubscriptionType(sub) if sub else None

    @strawberry.field(name="getSubscriptionFeatures")
    async def get_subscription_features(
        self,
        info: strawberry.Info,
    ) -> Optional[SubscriptionFeaturesType]:
        """Fetch resolved feature flags for the current tenant's active plan."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant context missing. Provide X-Tenant-ID header.")
        db = info.context.db
        features = await TenantSubscriptionService.get_subscription_features(db, tenant_id)
        return SubscriptionFeaturesType(features) if features else None

    @strawberry.field(name="getTenantSubscriptionPayments")
    async def get_tenant_subscription_payments(
        self,
        info: strawberry.Info,
        tenant_subscription_id: uuid.UUID = strawberry.field(name="tenantSubscriptionId"),
    ) -> List[TenantSubscriptionPaymentType]:
        """Fetch all payments for a given tenant subscription (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can view subscription payments.")
        db = info.context.db
        payments = await TenantSubscriptionPaymentService.get_payments_by_subscription(
            db, tenant_subscription_id
        )
        return [TenantSubscriptionPaymentType(p) for p in payments]


# ===========================================================================
# Mutations
# ===========================================================================

@strawberry.type
class SubscriptionMutation:

    @strawberry.mutation(name="createSubscriptionPlan")
    async def create_subscription_plan(
        self,
        info: strawberry.Info,
        input: CreateSubscriptionPlanInput,
    ) -> SubscriptionPlanType:
        """Create a new subscription plan (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can manage subscription plans.")

        db = info.context.db
        plan = await SubscriptionPlanService.create_plan(
            db=db,
            title=input.title,
            price=input.price,
            billing_cycle=input.billing_cycle,
            type=input.type,
            description=input.description,
            is_active=input.is_active,
            actor_user_id=str(current_user.id),
        )
        return SubscriptionPlanType(plan)

    @strawberry.mutation(name="updateSubscriptionPlan")
    async def update_subscription_plan(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
        input: UpdateSubscriptionPlanInput,
    ) -> SubscriptionPlanType:
        """Update an existing subscription plan (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can manage subscription plans.")

        db = info.context.db
        kwargs = {}
        for field in ["title", "price", "billing_cycle", "type", "description", "is_active"]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        plan = await SubscriptionPlanService.update_plan(
            db=db,
            plan_id=id,
            actor_user_id=str(current_user.id),
            **kwargs,
        )
        return SubscriptionPlanType(plan)

    @strawberry.mutation(name="deleteSubscriptionPlan")
    async def delete_subscription_plan(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
    ) -> bool:
        """Delete a subscription plan (Requires SUPER_ADMIN). Fails if active tenants use it."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can delete subscription plans.")

        db = info.context.db
        return await SubscriptionPlanService.delete_plan(
            db=db,
            plan_id=id,
            actor_user_id=str(current_user.id),
        )

    @strawberry.mutation(name="createSubscriptionFeatures")
    async def create_subscription_features(
        self,
        info: strawberry.Info,
        input: CreateSubscriptionFeaturesInput,
    ) -> SubscriptionFeaturesType:
        """Create feature configuration for a plan (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can manage subscription features.")

        db = info.context.db
        features = await SubscriptionFeaturesService.create_features(
            db=db,
            plan_id=input.plan_id,
            user_limit=input.user_limit,
            product_limit=input.product_limit,
            coupon_limit=input.coupon_limit,
            cod_enabled=bool(input.cod_enabled),
            cms_enabled=bool(input.cms_enabled),
            otp_login_enabled=bool(input.otp_login_enabled),
            custom_domain_enabled=bool(input.custom_domain_enabled),
            actor_user_id=str(current_user.id),
        )
        return SubscriptionFeaturesType(features)

    @strawberry.mutation(name="updateSubscriptionFeatures")
    async def update_subscription_features(
        self,
        info: strawberry.Info,
        plan_id: uuid.UUID = strawberry.field(name="planId"),
        input: UpdateSubscriptionFeaturesInput = strawberry.argument(),
    ) -> SubscriptionFeaturesType:
        """Update feature configuration for a plan (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can manage subscription features.")

        db = info.context.db
        kwargs = {}
        for field in [
            "user_limit", "product_limit", "coupon_limit",
            "cod_enabled", "cms_enabled", "otp_login_enabled", "custom_domain_enabled",
        ]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        features = await SubscriptionFeaturesService.update_features(
            db=db,
            plan_id=plan_id,
            actor_user_id=str(current_user.id),
            **kwargs,
        )
        return SubscriptionFeaturesType(features)

    @strawberry.mutation(name="subscribeTenant")
    async def subscribe_tenant(
        self,
        info: strawberry.Info,
        input: SubscribeTenantInput,
    ) -> TenantSubscriptionType:
        """Subscribe the current tenant to a plan (Requires TENANT_ADMIN or SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can manage tenant subscriptions.")

        tenant_id = info.context.tenant_id
        if not tenant_id:
            if current_user.tenant_id:
                tenant_id = current_user.tenant_id
            else:
                raise ValidationError("Tenant context missing. Provide X-Tenant-ID header.")

        db = info.context.db
        subscription = await TenantSubscriptionService.subscribe_tenant(
            db=db,
            tenant_id=tenant_id,
            plan_id=input.plan_id,
            start_date=input.start_date,
            end_date=input.end_date,
            status=input.status or "ACTIVE",
            coupon_id=input.coupon_id,
            remark=input.remark,
            actor_user_id=str(current_user.id),
        )
        return TenantSubscriptionType(subscription)

    @strawberry.mutation(name="renewTenantSubscription")
    async def renew_tenant_subscription(
        self,
        info: strawberry.Info,
        input: RenewTenantSubscriptionInput,
    ) -> TenantSubscriptionType:
        """Renew the current tenant's subscription (cancels existing and creates new)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can renew tenant subscriptions.")

        tenant_id = info.context.tenant_id
        if not tenant_id:
            if current_user.tenant_id:
                tenant_id = current_user.tenant_id
            else:
                raise ValidationError("Tenant context missing. Provide X-Tenant-ID header.")

        db = info.context.db
        subscription = await TenantSubscriptionService.renew_subscription(
            db=db,
            tenant_id=tenant_id,
            plan_id=input.plan_id,
            start_date=input.start_date,
            end_date=input.end_date,
            coupon_id=input.coupon_id,
            remark=input.remark,
            actor_user_id=str(current_user.id),
        )
        return TenantSubscriptionType(subscription)

    @strawberry.mutation(name="cancelTenantSubscription")
    async def cancel_tenant_subscription(
        self,
        info: strawberry.Info,
        remark: Optional[str] = None,
    ) -> TenantSubscriptionType:
        """Cancel the current tenant's active subscription."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can cancel tenant subscriptions.")

        tenant_id = info.context.tenant_id
        if not tenant_id:
            if current_user.tenant_id:
                tenant_id = current_user.tenant_id
            else:
                raise ValidationError("Tenant context missing. Provide X-Tenant-ID header.")

        db = info.context.db
        subscription = await TenantSubscriptionService.cancel_subscription(
            db=db,
            tenant_id=tenant_id,
            remark=remark,
            actor_user_id=str(current_user.id),
        )
        return TenantSubscriptionType(subscription)

    @strawberry.mutation(name="createTenantSubscriptionPayment")
    async def create_tenant_subscription_payment(
        self,
        info: strawberry.Info,
        input: CreateTenantSubscriptionPaymentInput,
    ) -> TenantSubscriptionPaymentType:
        """Record a payment for a tenant subscription (Requires TENANT_ADMIN or SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can record subscription payments.")

        db = info.context.db
        payment = await TenantSubscriptionPaymentService.create_payment(
            db=db,
            tenant_subscription_id=input.tenant_subscription_id,
            amount=input.amount,
            payment_method=input.payment_method,
            status=input.status or "PENDING",
            transaction_id=input.transaction_id,
            paid_at=input.paid_at,
            actor_user_id=str(current_user.id),
        )
        return TenantSubscriptionPaymentType(payment)
