import uuid
from datetime import datetime
from typing import Optional, List
import strawberry

from app.promotions.models import Coupon as DBCoupon
from app.promotions.services import coupon_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class CouponType:
    """GraphQL representation of a Coupon."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    code: str
    description: Optional[str]
    discount_type: str = strawberry.field(name="discountType")
    discount_value: float = strawberry.field(name="discountValue")
    min_order_value: float = strawberry.field(name="minOrderValue")
    max_discount_amount: Optional[float] = strawberry.field(name="maxDiscountAmount")
    start_date: datetime = strawberry.field(name="startDate")
    end_date: datetime = strawberry.field(name="endDate")
    usage_limit_total: Optional[int] = strawberry.field(name="usageLimitTotal")
    usage_limit_per_user: int = strawberry.field(name="usageLimitPerUser")
    usage_count: int = strawberry.field(name="usageCount")
    is_active: bool = strawberry.field(name="isActive")
    rules: strawberry.scalars.JSON

    def __init__(self, db_coupon: DBCoupon):
        self.id = db_coupon.id
        self.tenant_id = db_coupon.tenant_id
        self.code = db_coupon.code
        self.description = db_coupon.description
        self.discount_type = db_coupon.discount_type
        self.discount_value = float(db_coupon.discount_value)
        self.min_order_value = float(db_coupon.min_order_value)
        self.max_discount_amount = float(db_coupon.max_discount_amount) if db_coupon.max_discount_amount is not None else None
        self.start_date = db_coupon.start_date
        self.end_date = db_coupon.end_date
        self.usage_limit_total = db_coupon.usage_limit_total
        self.usage_limit_per_user = db_coupon.usage_limit_per_user
        self.usage_count = db_coupon.usage_count
        self.is_active = db_coupon.is_active
        self.rules = db_coupon.rules


@strawberry.type
class CartDiscountResult:
    """GraphQL representation of a simulated or applied coupon discount result."""
    is_valid: bool = strawberry.field(name="isValid")
    error_message: Optional[str] = strawberry.field(name="errorMessage")
    discount_applied: float = strawberry.field(name="discountApplied")
    new_total: float = strawberry.field(name="newTotal")
    original_total: float = strawberry.field(name="originalTotal")


@strawberry.input
class CreateCouponInput:
    code: str
    discount_type: str = strawberry.field(name="discountType")  # FLAT, PERCENTAGE
    discount_value: float = strawberry.field(name="discountValue")
    start_date: datetime = strawberry.field(name="startDate")
    end_date: datetime = strawberry.field(name="endDate")
    description: Optional[str] = None
    min_order_value: float = strawberry.field(default=0.00, name="minOrderValue")
    max_discount_amount: Optional[float] = strawberry.field(default=None, name="maxDiscountAmount")
    usage_limit_total: Optional[int] = strawberry.field(default=None, name="usageLimitTotal")
    usage_limit_per_user: int = strawberry.field(default=1, name="usageLimitPerUser")
    rules: Optional[strawberry.scalars.JSON] = strawberry.field(default=None)


@strawberry.type
class CouponQuery:
    @strawberry.field
    async def coupon(self, info: strawberry.Info, code: str) -> Optional[CouponType]:
        """Fetch details of a coupon code by code."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_coupon = await coupon_service.get_coupon_by_code(db, tenant_id, code)
        return CouponType(db_coupon) if db_coupon else None

    @strawberry.field
    async def coupons(self, info: strawberry.Info) -> List[CouponType]:
        """Fetch all promotional coupons (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can list all coupon codes.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_coupons = await coupon_service.get_coupons(db, tenant_id)
        return [CouponType(c) for c in db_coupons]

    @strawberry.field
    async def simulate_coupon(self, info: strawberry.Info, code: str) -> CartDiscountResult:
        """Simulate applying a coupon code on the active user's shopping cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        calc = await coupon_service.calculate_discount(db, tenant_id, current_user.id, [code])
        return CartDiscountResult(
            is_valid=calc["is_valid"],
            error_message=calc["error_message"],
            discount_applied=float(calc["discount_applied"]),
            new_total=float(calc["new_total"]),
            original_total=float(calc["original_total"])
        )


@strawberry.type
class CouponMutation:
    @strawberry.mutation
    async def create_coupon(self, info: strawberry.Info, input: CreateCouponInput) -> CouponType:
        """Create a new promotional coupon code (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can create coupon codes.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_coupon = await coupon_service.create_coupon(
            db=db,
            tenant_id=tenant_id,
            code=input.code,
            discount_type=input.discount_type,
            discount_value=input.discount_value,
            start_date=input.start_date,
            end_date=input.end_date,
            description=input.description,
            min_order_value=input.min_order_value,
            max_discount_amount=input.max_discount_amount,
            usage_limit_total=input.usage_limit_total,
            usage_limit_per_user=input.usage_limit_per_user,
            rules=input.rules
        )
        return CouponType(db_coupon)

    @strawberry.mutation
    async def update_coupon_status(self, info: strawberry.Info, id: uuid.UUID, is_active: bool) -> CouponType:
        """Activate or deactivate a coupon code (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only admins can modify coupon codes.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_coupon = await coupon_service.update_coupon_status(db, tenant_id, id, is_active)
        return CouponType(db_coupon)

    @strawberry.mutation
    async def apply_coupon(self, info: strawberry.Info, code: str, order_id: uuid.UUID) -> CartDiscountResult:
        """Apply a coupon code, write a ledger entry, and increment the coupon usage counter."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        calc = await coupon_service.apply_coupon(db, tenant_id, current_user.id, code, order_id)
        return CartDiscountResult(
            is_valid=calc["is_valid"],
            error_message=calc["error_message"],
            discount_applied=float(calc["discount_applied"]),
            new_total=float(calc["new_total"]),
            original_total=float(calc["original_total"])
        )
