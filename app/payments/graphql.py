import uuid
from typing import Optional, List, Annotated
import strawberry
from decimal import Decimal

from app.utils.exceptions import UnauthorizedError, ValidationError
from app.payments.models import PaymentGateway, TenantPaymentGateway, TenantCommission
from app.payments.services import PaymentGatewayService
from sqlalchemy.future import select

@strawberry.type
class PaymentGatewayType:
    id: uuid.UUID
    name: str
    credentials: strawberry.scalars.JSON
    webhook_secret: Optional[str] = strawberry.field(name="webhookSecret")
    is_active: bool = strawberry.field(name="isActive")

    def __init__(self, db_model: PaymentGateway):
        self.id = db_model.id
        self.name = db_model.name
        self.credentials = db_model.credentials
        self.webhook_secret = db_model.webhook_secret
        self.is_active = db_model.is_active


@strawberry.type
class TenantPaymentGatewayType:
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    gateway_id: uuid.UUID = strawberry.field(name="gatewayId")
    credentials: strawberry.scalars.JSON
    webhook_secret: Optional[str] = strawberry.field(name="webhookSecret")
    is_active: bool = strawberry.field(name="isActive")

    def __init__(self, db_model: TenantPaymentGateway):
        self.id = db_model.id
        self.tenant_id = db_model.tenant_id
        self.gateway_id = db_model.gateway_id
        self.credentials = db_model.credentials
        self.webhook_secret = db_model.webhook_secret
        self.is_active = db_model.is_active


@strawberry.type
class TenantCommissionType:
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    commission_percent: float = strawberry.field(name="commissionPercent")
    linked_account_id: str = strawberry.field(name="linkedAccountId")

    def __init__(self, db_model: TenantCommission):
        self.id = db_model.id
        self.tenant_id = db_model.tenant_id
        self.commission_percent = float(db_model.commission_percent)
        self.linked_account_id = db_model.linked_account_id


@strawberry.type
class InitiatePaymentResult:
    key: str
    amount: int
    currency: str
    name: str
    order_id: str = strawberry.field(name="orderId")
    payment_id: str = strawberry.field(name="paymentId")


@strawberry.input
class ConfigurePlatformGatewayInput:
    name: str
    credentials: strawberry.scalars.JSON
    webhook_secret: Optional[str] = strawberry.field(default=None, name="webhookSecret")
    is_active: bool = strawberry.field(default=False, name="isActive")


@strawberry.input
class ConfigureTenantGatewayInput:
    gateway_id: uuid.UUID = strawberry.field(name="gatewayId")
    credentials: strawberry.scalars.JSON
    webhook_secret: Optional[str] = strawberry.field(default=None, name="webhookSecret")
    is_active: bool = strawberry.field(default=False, name="isActive")


@strawberry.input
class ConfigureTenantCommissionInput:
    commission_percent: float = strawberry.field(name="commissionPercent")
    linked_account_id: str = strawberry.field(name="linkedAccountId")


@strawberry.type
class PaymentQuery:
    @strawberry.field
    async def platform_gateways(self, info: strawberry.Info) -> List[PaymentGatewayType]:
        """List all platform-level payment gateways (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Access denied. SUPER_ADMIN role required.")

        db = info.context.db
        stmt = select(PaymentGateway)
        res = await db.execute(stmt)
        gateways = res.scalars().all()
        return [PaymentGatewayType(g) for g in gateways]

    @strawberry.field
    async def active_platform_gateway(self, info: strawberry.Info) -> Optional[PaymentGatewayType]:
        """Fetch the currently active platform-level gateway."""
        db = info.context.db
        stmt = select(PaymentGateway).where(PaymentGateway.is_active == True)
        res = await db.execute(stmt)
        gw = res.scalar_one_or_none()
        return PaymentGatewayType(gw) if gw else None

    @strawberry.field
    async def tenant_gateways(self, info: strawberry.Info) -> List[TenantPaymentGatewayType]:
        """List all configured payment gateways for the current tenant (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Access denied. Admin role required.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        stmt = select(TenantPaymentGateway).where(TenantPaymentGateway.tenant_id == tenant_id)
        res = await db.execute(stmt)
        gws = res.scalars().all()
        return [TenantPaymentGatewayType(g) for g in gws]

    @strawberry.field
    async def tenant_commission(self, info: strawberry.Info) -> Optional[TenantCommissionType]:
        """Fetch the commission routing configuration for the current tenant (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Access denied. Admin role required.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        stmt = select(TenantCommission).where(TenantCommission.tenant_id == tenant_id)
        res = await db.execute(stmt)
        comm = res.scalar_one_or_none()
        return TenantCommissionType(comm) if comm else None


@strawberry.type
class PaymentMutation:
    @strawberry.mutation
    async def configure_platform_gateway(
        self, info: strawberry.Info, input: ConfigurePlatformGatewayInput
    ) -> PaymentGatewayType:
        """Configure or update a platform gateway profile (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Access denied. SUPER_ADMIN role required.")

        db = info.context.db
        gateway = await PaymentGatewayService.configure_platform_gateway(
            db=db,
            name=input.name,
            credentials=input.credentials,
            webhook_secret=input.webhook_secret,
            is_active=input.is_active
        )
        return PaymentGatewayType(gateway)

    @strawberry.mutation
    async def activate_platform_gateway(self, info: strawberry.Info, id: uuid.UUID) -> PaymentGatewayType:
        """Activate a platform gateway and deactivate others (Requires SUPER_ADMIN)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Access denied. SUPER_ADMIN role required.")

        db = info.context.db
        gateway = await PaymentGatewayService.activate_platform_gateway(db, id)
        return PaymentGatewayType(gateway)

    @strawberry.mutation
    async def configure_tenant_gateway(
        self, info: strawberry.Info, input: ConfigureTenantGatewayInput
    ) -> TenantPaymentGatewayType:
        """Configure a tenant-specific gateway credential (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Access denied. Admin role required.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        tgw = await PaymentGatewayService.configure_tenant_gateway(
            db=db,
            tenant_id=tenant_id,
            gateway_id=input.gateway_id,
            credentials=input.credentials,
            webhook_secret=input.webhook_secret,
            is_active=input.is_active
        )
        return TenantPaymentGatewayType(tgw)

    @strawberry.mutation
    async def activate_tenant_gateway(self, info: strawberry.Info, id: uuid.UUID) -> TenantPaymentGatewayType:
        """Activate a tenant gateway and deactivate others (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Access denied. Admin role required.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        tgw = await PaymentGatewayService.activate_tenant_gateway(db, tenant_id, id)
        return TenantPaymentGatewayType(tgw)

    @strawberry.mutation
    async def configure_tenant_commission(
        self, info: strawberry.Info, input: ConfigureTenantCommissionInput
    ) -> TenantCommissionType:
        """Configure the commission percentage & linked routing account for platform fallback route (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Access denied. Admin role required.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        comm = await PaymentGatewayService.configure_tenant_commission(
            db=db,
            tenant_id=tenant_id,
            commission_percent=Decimal(str(input.commission_percent)),
            linked_account_id=input.linked_account_id
        )
        return TenantCommissionType(comm)

    @strawberry.mutation
    async def initiate_online_payment(self, info: strawberry.Info, order_id: uuid.UUID) -> InitiatePaymentResult:
        """Initiate payment for an order, creating a pending payment transaction (Requires Authenticated User)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        res = await PaymentGatewayService.initiate_payment(db, tenant_id, order_id)
        return InitiatePaymentResult(
            key=res["key"],
            amount=res["amount"],
            currency=res["currency"],
            name=res["name"],
            order_id=res["order_id"],
            payment_id=res["payment_id"]
        )

    @strawberry.mutation
    async def initiate_cart_payment(self, info: strawberry.Info) -> InitiatePaymentResult:
        """Initiate payment for the current user's cart (Requires Authenticated User)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        res = await PaymentGatewayService.initiate_cart_payment(db, tenant_id, current_user.id)
        return InitiatePaymentResult(
            key=res["key"],
            amount=res["amount"],
            currency=res["currency"],
            name=res["name"],
            order_id=res["order_id"],
            payment_id=res["payment_id"]
        )

    @strawberry.mutation
    async def verify_online_payment(
        self,
        info: strawberry.Info,
        order_id: uuid.UUID,
        payment_id: str,
        signature: str
    ) -> Annotated["OrderType", strawberry.lazy("app.orders.graphql")]:
        """Verify an online Razorpay payment and mark the order as PAID."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        order = await PaymentGatewayService.verify_online_payment(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            order_id=order_id,
            payment_id=payment_id,
            signature=signature
        )
        from app.orders.graphql import OrderType
        return OrderType(order)
