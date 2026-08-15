import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.promotions.models import Coupon, CouponUsage
from app.users.models import UserCart, CartItem
from app.products.products.models import Product
from app.products.pricing.models import ProductPrice, PricingType
from app.products.categories.models import ProductCategory
from app.utils.exceptions import ValidationError
from app.utils.audit import log_audit_event

def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        from datetime import timezone
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

class CouponService:
    """Service layer handling creation, retrieval, validation, and lifecycle of promotion coupons."""

    @staticmethod
    async def create_coupon(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        code: str,
        discount_type: str,
        discount_value: float,
        start_date: datetime,
        end_date: datetime,
        description: Optional[str] = None,
        min_order_value: float = 0.00,
        max_discount_amount: Optional[float] = None,
        usage_limit_total: Optional[int] = None,
        usage_limit_per_user: int = 1,
        rules: Optional[Dict[str, Any]] = None
    ) -> Coupon:
        """Create a new promotional coupon code under a tenant."""
        start_date = to_naive_utc(start_date)
        end_date = to_naive_utc(end_date)

        # 1. Normalize code to uppercase
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValidationError("Coupon code cannot be empty.")

        # 2. Check if coupon code already exists under this tenant
        stmt = select(Coupon).where((Coupon.tenant_id == tenant_id) & (Coupon.code == normalized_code))
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ValidationError(f"Coupon code '{normalized_code}' already exists under this tenant.")

        if discount_value <= 0:
            raise ValidationError("Discount value must be greater than zero.")

        if start_date >= end_date:
            raise ValidationError("Start date must be before end date.")

        coupon = Coupon(
            tenant_id=tenant_id,
            code=normalized_code,
            description=description,
            discount_type=discount_type.upper(),
            discount_value=Decimal(str(discount_value)),
            min_order_value=Decimal(str(min_order_value)),
            max_discount_amount=Decimal(str(max_discount_amount)) if max_discount_amount is not None else None,
            start_date=start_date,
            end_date=end_date,
            usage_limit_total=usage_limit_total,
            usage_limit_per_user=usage_limit_per_user,
            rules=rules or {},
            is_active=True
        )
        db.add(coupon)
        await db.commit()
        await db.refresh(coupon)

        await log_audit_event(
            action="COUPON_CREATED",
            tenant_id=str(tenant_id),
            details={"coupon_id": str(coupon.id), "code": normalized_code}
        )

        return coupon

    @staticmethod
    async def get_coupon_by_code(db: AsyncSession, tenant_id: uuid.UUID, code: str) -> Optional[Coupon]:
        """Fetch a coupon code by matching case-insensitively within a tenant."""
        stmt = select(Coupon).where((Coupon.tenant_id == tenant_id) & (Coupon.code == code.strip().upper()))
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
    @staticmethod
    async def get_coupons(db: AsyncSession, tenant_id: uuid.UUID) -> List[Coupon]:
        """Fetch all coupons under a tenant."""
        stmt = select(Coupon).where(Coupon.tenant_id == tenant_id).order_by(Coupon.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def update_coupon_status(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        coupon_id: uuid.UUID,
        is_active: bool
    ) -> Coupon:
        """Enable or disable a coupon code."""
        stmt = select(Coupon).where((Coupon.tenant_id == tenant_id) & (Coupon.id == coupon_id))
        res = await db.execute(stmt)
        coupon = res.scalar_one_or_none()
        if not coupon:
            raise ValidationError("Coupon not found.")

        coupon.is_active = is_active
        await db.commit()
        await db.refresh(coupon)
        return coupon

    @staticmethod
    @staticmethod
    async def calculate_discount(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        codes: List[str]
    ) -> Dict[str, Any]:
        """Calculate discount details for the authenticated user's cart without altering database state.
        
        Returns:
            {
                "is_valid": bool,
                "error_message": Optional[str],
                "discount_applied": Decimal,
                "new_total": Decimal,
                "original_total": Decimal,
                "coupon": Optional[Coupon]
            }
        """
        # 1. Fetch User's Cart
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            return {
                "is_valid": False,
                "error_message": "Your shopping cart is empty.",
                "discount_applied": Decimal("0.00"),
                "new_total": Decimal("0.00"),
                "original_total": Decimal("0.00"),
                "coupon": None
            }

        # 2. Fetch Cart Items with Product Details and Selling Price
        stmt_items = select(
            CartItem.product_id,
            CartItem.quantity,
            ProductPrice.price
        ).join(
            Product, Product.id == CartItem.product_id
        ).join(
            ProductPrice, ProductPrice.product_id == Product.id
        ).join(
            PricingType, PricingType.id == ProductPrice.pricing_type_id
        ).where(
            (CartItem.cart_id == cart.id) &
            (PricingType.tenant_id == tenant_id) &
            (PricingType.type == "selling_price")
        )
        res_items = await db.execute(stmt_items)
        cart_products = res_items.all()

        total_cart_value = Decimal("0.00")
        for product_id, quantity, price in cart_products:
            total_cart_value += Decimal(str(price)) * quantity

        if not codes:
            return {
                "is_valid": True,
                "error_message": None,
                "discount_applied": Decimal("0.00"),
                "new_total": total_cart_value.quantize(Decimal("0.01")),
                "original_total": total_cart_value.quantize(Decimal("0.01")),
                "coupon": None
            }

        if not cart_products:
            return {
                "is_valid": False,
                "error_message": "Your cart contains no priced products.",
                "discount_applied": Decimal("0.00"),
                "new_total": Decimal("0.00"),
                "original_total": Decimal("0.00"),
                "coupon": None
            }

        current_total = total_cart_value
        total_discount = Decimal("0.00")
        last_coupon = None
        has_valid_coupon = False
        first_error = None

        for code in codes:
            # 1. Fetch Coupon
            coupon = await CouponService.get_coupon_by_code(db, tenant_id, code)
            if not coupon:
                if not first_error:
                    first_error = "Coupon code not found."
                continue

            # 2. Check general active status
            if not coupon.is_active:
                if not first_error:
                    first_error = "This coupon code is inactive."
                continue

            # 3. Check validity dates
            now = datetime.utcnow()
            if now < coupon.start_date:
                if not first_error:
                    first_error = "This coupon promo has not started yet."
                continue
            if now > coupon.end_date:
                if not first_error:
                    first_error = "This coupon code has expired."
                continue

            # 4. Check global usage limits
            if coupon.usage_limit_total is not None and coupon.usage_count >= coupon.usage_limit_total:
                if not first_error:
                    first_error = "This coupon code limit has been reached."
                continue

            # 5. Check user-specific limit
            stmt_user_uses = select(func.count(CouponUsage.id)).where(
                (CouponUsage.coupon_id == coupon.id) &
                (CouponUsage.user_id == user_id)
            )
            res_user_uses = await db.execute(stmt_user_uses)
            user_uses_count = res_user_uses.scalar() or 0
            if user_uses_count >= coupon.usage_limit_per_user:
                if not first_error:
                    first_error = "You have already reached the redemption limit for this coupon."
                continue

            # 6. Check min order value against original total cart value
            if total_cart_value < coupon.min_order_value:
                if not first_error:
                    first_error = f"Minimum order value of {coupon.min_order_value} required for this coupon."
                continue

            # 7. Evaluate dynamic eligibility rules for this coupon
            rules = coupon.rules or {}
            exclude_products = [uuid.UUID(p) for p in rules.get("exclude_products", [])]
            only_products = [uuid.UUID(p) for p in rules.get("only_products", [])]
            exclude_categories = [uuid.UUID(c) for c in rules.get("exclude_categories", [])]
            only_categories = [uuid.UUID(c) for c in rules.get("only_categories", [])]

            eligible_total = Decimal("0.00")
            for product_id, quantity, price in cart_products:
                subtotal = Decimal(str(price)) * quantity
                
                # Fetch product categories
                stmt_cats = select(ProductCategory.category_id).where(ProductCategory.product_id == product_id)
                res_cats = await db.execute(stmt_cats)
                product_category_ids = [r[0] for r in res_cats.all()]

                is_eligible = True
                if exclude_products and product_id in exclude_products:
                    is_eligible = False
                elif only_products and product_id not in only_products:
                    is_eligible = False

                if is_eligible:
                    if exclude_categories and any(c in exclude_categories for c in product_category_ids):
                        is_eligible = False
                    elif only_categories and not any(c in only_categories for c in product_category_ids):
                        is_eligible = False

                if is_eligible:
                    eligible_total += subtotal

            if eligible_total <= 0:
                if not first_error:
                    first_error = "No eligible products in your cart for this promotion."
                continue

            # Apply previous discounts to scale eligible total (sequential compounding)
            remaining_ratio = current_total / total_cart_value if total_cart_value > 0 else Decimal("1.00")
            scaled_eligible_total = eligible_total * remaining_ratio

            # Calculate discount
            discount = Decimal("0.00")
            if coupon.discount_type == "PERCENTAGE":
                discount = scaled_eligible_total * (coupon.discount_value / Decimal("100.00"))
                if coupon.max_discount_amount is not None:
                    discount = min(discount, coupon.max_discount_amount)
            elif coupon.discount_type == "FLAT":
                discount = min(coupon.discount_value, scaled_eligible_total)
            elif coupon.discount_type == "FREE_SHIPPING":
                discount = Decimal("0.00")

            discount = discount.quantize(Decimal("0.01"))
            # Ensure discount doesn't exceed current remaining cart total
            discount = min(discount, current_total)

            current_total = max(Decimal("0.00"), current_total - discount)
            total_discount += discount
            last_coupon = coupon
            has_valid_coupon = True

        if not has_valid_coupon and first_error:
            return {
                "is_valid": False,
                "error_message": first_error,
                "discount_applied": Decimal("0.00"),
                "new_total": total_cart_value.quantize(Decimal("0.01")),
                "original_total": total_cart_value.quantize(Decimal("0.01")),
                "coupon": None
            }

        return {
            "is_valid": True,
            "error_message": None,
            "discount_applied": total_discount.quantize(Decimal("0.01")),
            "new_total": current_total.quantize(Decimal("0.01")),
            "original_total": total_cart_value.quantize(Decimal("0.01")),
            "coupon": last_coupon
        }

    @staticmethod
    async def apply_coupon(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        code: str,
        order_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Apply a coupon code, check constraints, write to ledger, and increment usage count."""
        # 1. Calculate discount first to validate eligibility
        calc = await CouponService.calculate_discount(db, tenant_id, user_id, [code])
        if not calc["is_valid"]:
            raise ValidationError(calc["error_message"])

        coupon = calc["coupon"]

        # 2. Insert Coupon Usage record (Ledger Entry)
        usage = CouponUsage(
            tenant_id=tenant_id,
            coupon_id=coupon.id,
            user_id=user_id,
            order_id=order_id,
            discount_applied=calc["discount_applied"]
        )
        db.add(usage)

        # 3. Increment Coupon usage count
        coupon.usage_count += 1
        
        await db.commit()
        await db.refresh(usage)
        await db.refresh(coupon)

        await log_audit_event(
            action="COUPON_REDEEMED",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            details={
                "coupon_id": str(coupon.id),
                "code": coupon.code,
                "order_id": str(order_id),
                "discount_applied": str(calc["discount_applied"])
            }
        )

        return calc

    @staticmethod
    async def apply_coupon_to_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        code: str
    ) -> UserCart:
        """Apply a coupon to the user's cart. Does not increment usage count."""
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValidationError("Coupon code cannot be empty.")

        # 1. Fetch Tenant details
        from app.tenants.models import Tenant
        stmt_tenant = select(Tenant).where(Tenant.id == tenant_id)
        res_tenant = await db.execute(stmt_tenant)
        tenant = res_tenant.scalar_one_or_none()
        if not tenant:
            raise ValidationError("Tenant not found.")

        # 2. Fetch User's Cart
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            from app.users.services import user_service
            cart = await user_service.get_or_create_cart(db, tenant_id, user_id)

        # 3. Validate the coupon code itself
        calc = await CouponService.calculate_discount(db, tenant_id, user_id, [normalized_code])
        if not calc["is_valid"]:
            raise ValidationError(calc["error_message"])

        # 4. Check if coupon is already applied
        applied = list(cart.applied_coupons or [])
        if normalized_code in applied:
            raise ValidationError(f"Coupon '{normalized_code}' is already applied.")

        # 5. Append or Replace based on tenant configuration
        if tenant.allow_multiple_coupons:
            applied.append(normalized_code)
        else:
            applied = [normalized_code]

        # Update and save
        cart.applied_coupons = applied
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cart, "applied_coupons")
        await db.commit()
        await db.refresh(cart)
        return cart

    @staticmethod
    async def remove_coupon_from_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        code: str
    ) -> UserCart:
        """Remove a coupon from the user's cart."""
        normalized_code = code.strip().upper()
        
        # 1. Fetch User's Cart
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            raise ValidationError("Cart not found.")

        applied = list(cart.applied_coupons or [])
        if normalized_code not in applied:
            raise ValidationError(f"Coupon '{normalized_code}' is not applied to this cart.")

        applied.remove(normalized_code)
        cart.applied_coupons = applied
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cart, "applied_coupons")
        await db.commit()
        await db.refresh(cart)
        return cart

    @staticmethod
    async def clear_coupons_from_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> UserCart:
        """Clear all coupons from the user's cart."""
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            raise ValidationError("Cart not found.")

        cart.applied_coupons = []
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cart, "applied_coupons")
        await db.commit()
        await db.refresh(cart)
        return cart


coupon_service = CouponService()
