import uuid
from datetime import datetime
from typing import Optional, Annotated
from enum import Enum
import strawberry

from app.users.models import (
    User as DBUser,
    UserAddress as DBUserAddress,
)
from app.users.services import user_service
from app.utils.exceptions import UnauthorizedError, ValidationError
from app.tenants.graphql import TenantType
from app.media.graphql import MediaType, CreateMediaInput
from app.products.products.graphql import ProductType
from app.promotions.graphql import CouponType

@strawberry.enum
class UserRole(Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    USER = "USER"

@strawberry.enum
class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


@strawberry.type
class UserAddressType:
    """GraphQL representation of a User's Address."""
    id: uuid.UUID
    user_id: uuid.UUID
    address_line_1: str = strawberry.field(name="addressLine1")
    address_line_2: Optional[str] = strawberry.field(name="addressLine2")
    landmark: Optional[str]
    pincode: str
    state: str
    district: str
    customer_name: str = strawberry.field(name="customerName")
    phone_number: str = strawberry.field(name="phoneNumber")
    is_primary: bool = strawberry.field(name="isPrimary")
    lat_long: Optional[str] = strawberry.field(name="latLong")
    third_party_app_address: Optional[str] = strawberry.field(name="thirdPartyAppAddress")
    created_at: datetime
    updated_at: datetime

    def __init__(self, db_address: DBUserAddress):
        self.id = db_address.id
        self.user_id = db_address.user_id
        self.address_line_1 = db_address.address_line_1
        self.address_line_2 = db_address.address_line_2
        self.landmark = db_address.landmark
        self.pincode = db_address.pincode
        self.state = db_address.state
        self.district = db_address.district
        self.customer_name = db_address.customer_name
        self.phone_number = db_address.phone_number
        self.is_primary = db_address.is_primary
        self.lat_long = db_address.lat_long
        self.third_party_app_address = db_address.third_party_app_address
        self.created_at = db_address.created_at
        self.updated_at = db_address.updated_at


@strawberry.type
class CartItemType:
    id: uuid.UUID
    cart_id: uuid.UUID = strawberry.field(name="cartId")
    user_id: uuid.UUID = strawberry.field(name="userId")
    product_id: uuid.UUID = strawberry.field(name="productId")
    quantity: int
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def product(self, info: strawberry.Info) -> ProductType:
        from app.products.products.services import product_service
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_product = await product_service.get_product_by_id(tenant_id, self.product_id)
        if not db_product:
            raise ValidationError("Product not found.")
        return ProductType(db_product)

    def __init__(self, db_item):
        self.id = db_item.id
        self.cart_id = db_item.cart_id
        self.user_id = db_item.user_id
        self.product_id = db_item.product_id
        self.quantity = db_item.quantity
        self.created_at = db_item.created_at
        self.updated_at = db_item.updated_at


@strawberry.type
class BillSummaryType:
    item_total: float = strawberry.field(name="itemTotal")
    discount_applied: float = strawberry.field(name="discountApplied")
    delivery_fee: float = strawberry.field(name="deliveryFee")
    tax: float = strawberry.field(name="tax")
    grand_total: float = strawberry.field(name="grandTotal")

@strawberry.type
class UserCartType:
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    delivery_fee: Optional[float] = strawberry.field(name="deliveryFee")
    delivery_service: Optional[str] = strawberry.field(name="deliveryService")
    estimated_days: Optional[int] = strawberry.field(name="estimatedDays")
    delivery_address_id: Optional[uuid.UUID] = strawberry.field(name="deliveryAddressId")
    created_at: datetime
    updated_at: datetime

    applied_coupon_codes: strawberry.Private[list[str]]

    @strawberry.field
    async def items(self, info: strawberry.Info) -> list[CartItemType]:
        db = info.context.db
        from app.users.models import CartItem
        from sqlalchemy.future import select
        stmt = select(CartItem).where(CartItem.cart_id == self.id)
        res = await db.execute(stmt)
        db_items = res.scalars().all()
        return [CartItemType(item) for item in db_items]

    @strawberry.field
    async def applied_coupons(self, info: strawberry.Info) -> list[CouponType]:
        from app.promotions.services import coupon_service
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        coupons = []
        for code in self.applied_coupon_codes:
            c = await coupon_service.get_coupon_by_code(db, tenant_id, code)
            if c:
                coupons.append(CouponType(c))
        return coupons

    @strawberry.field
    async def delivery_address(self, info: strawberry.Info) -> Optional[UserAddressType]:
        if not self.delivery_address_id:
            return None
        db = info.context.db
        from app.users.models import UserAddress
        from sqlalchemy.future import select
        stmt = select(UserAddress).where(UserAddress.id == self.delivery_address_id)
        res = await db.execute(stmt)
        addr = res.scalar_one_or_none()
        return UserAddressType(addr) if addr else None

    @strawberry.field
    async def bill_summary(self, info: strawberry.Info) -> BillSummaryType:
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        # Fetch the shipping address (pincode) if delivery_address_id is set on the cart.
        from sqlalchemy.future import select
        from decimal import Decimal
        pincode = None
        if self.delivery_address_id:
            from app.users.models import UserAddress
            stmt_addr = select(UserAddress.pincode).where(UserAddress.id == self.delivery_address_id)
            res_addr = await db.execute(stmt_addr)
            pincode = res_addr.scalar_one_or_none()

        # 1. Fetch Cart Items and calculate dynamic pricing using PricingService
        from app.users.models import CartItem
        from app.products.products.models import ProductStock
        from app.products.pricing.services import PricingService

        stmt_items = select(
            CartItem.product_id,
            CartItem.quantity,
            ProductStock.stock
        ).outerjoin(
            ProductStock, ProductStock.product_id == CartItem.product_id
        ).where(
            CartItem.cart_id == self.id
        )
        res_items = await db.execute(stmt_items)
        items = res_items.all()

        item_total = Decimal("0.00")
        for product_id, qty, stock in items:
            effective_price = await PricingService.get_effective_price(
                db=db,
                tenant_id=tenant_id,
                product_id=product_id,
                quantity=qty,
                location_id=None,
                pincode=pincode,
                current_time=None,
                current_stock=stock
            )
            item_total += effective_price * qty

        # 2. Calculate Coupon discount
        from app.promotions.services import coupon_service
        calc = await coupon_service.calculate_discount(db, tenant_id, self.user_id, self.applied_coupon_codes)
        discount_applied = calc["discount_applied"]

        # 3. Delivery Fee
        delivery_fee = Decimal(str(self.delivery_fee)) if self.delivery_fee is not None else Decimal("0.00")

        # 4. Net Total & Tax (5%) & Grand Total
        net_total = max(Decimal("0.00"), item_total - discount_applied + delivery_fee)
        tax = (net_total * Decimal("0.05")).quantize(Decimal("0.01"))
        grand_total = (net_total + tax).quantize(Decimal("0.01"))

        return BillSummaryType(
            item_total=float(item_total),
            discount_applied=float(discount_applied),
            delivery_fee=float(delivery_fee),
            tax=float(tax),
            grand_total=float(grand_total)
        )

    def __init__(self, db_cart):
        self.id = db_cart.id
        self.user_id = db_cart.user_id
        self.delivery_fee = float(db_cart.delivery_fee) if db_cart.delivery_fee is not None else None
        self.delivery_service = db_cart.delivery_service
        self.estimated_days = db_cart.estimated_days
        self.delivery_address_id = db_cart.delivery_address_id
        self.created_at = db_cart.created_at
        self.updated_at = db_cart.updated_at
        self.applied_coupon_codes = db_cart.applied_coupons or []





@strawberry.type
class UserType:
    """GraphQL representation of a User."""
    id: uuid.UUID
    name: str
    mobilenumber: str
    email: Optional[str]
    status: UserStatus
    role: UserRole
    tenant_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def tenant(self, info: strawberry.Info) -> Optional[TenantType]:
        """Resolve Tenant relationship for User."""
        if not self.tenant_id:
            return None
        from app.tenants.services import tenant_service
        db_tenant = await tenant_service.get_tenant_by_id(info.context.db, self.tenant_id)
        return TenantType(db_tenant) if db_tenant else None

    @strawberry.field
    async def wallet(self, info: strawberry.Info) -> Annotated["UserWalletType", strawberry.lazy("app.wallet.graphql")]:
        """Resolve UserWallet for User."""
        db = info.context.db
        from app.wallet.services import wallet_service
        from app.wallet.graphql import UserWalletType
        db_wallet = await wallet_service.get_or_create_wallet(db, self.id)
        return UserWalletType(db_wallet)

    @strawberry.field
    async def referral(self, info: strawberry.Info) -> Optional[Annotated["UserReferralType", strawberry.lazy("app.referral.graphql")]]:
        """Resolve UserReferral configuration for User."""
        db = info.context.db
        from sqlalchemy.future import select
        from app.referral.models import UserReferral
        from app.referral.graphql import UserReferralType
        stmt = select(UserReferral).where(UserReferral.user_id == self.id)
        res = await db.execute(stmt)
        db_ref = res.scalar_one_or_none()
        return UserReferralType(db_ref) if db_ref else None

    @strawberry.field
    async def addresses(self, info: strawberry.Info) -> list[UserAddressType]:
        """Resolve addresses list for User."""
        db = info.context.db
        db_addresses = await user_service.get_user_addresses(db, self.id)
        return [UserAddressType(addr) for addr in db_addresses]

    @strawberry.field
    async def media(self, info: strawberry.Info) -> list[MediaType]:
        """Resolve all associated media files for this user."""
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        from app.media.services import media_service
        db_media_list = await media_service.get_media_list(db, tenant_id, entity_name="user", entity_id=self.id)
        return [MediaType(m) for m in db_media_list]

    @strawberry.field
    async def cart(self, info: strawberry.Info) -> Optional[UserCartType]:
        """Resolve UserCart for User."""
        db = info.context.db
        from app.users.models import UserCart
        from sqlalchemy.future import select
        stmt = select(UserCart).where(UserCart.user_id == self.id)
        res = await db.execute(stmt)
        db_cart = res.scalar_one_or_none()
        return UserCartType(db_cart) if db_cart else None

    def __init__(self, db_user: DBUser):
        self.id = db_user.id
        self.name = db_user.name
        self.mobilenumber = db_user.mobilenumber
        self.email = db_user.email
        self.status = UserStatus(db_user.status)
        self.role = UserRole(db_user.role)
        self.tenant_id = db_user.tenant_id
        self.created_at = db_user.created_at
        self.updated_at = db_user.updated_at


@strawberry.input
class CreateUserInput:
    name: str
    mobilenumber: str
    email: Optional[str] = None
    password: Optional[str] = None
    role: UserRole = UserRole.USER
    media: Optional[list[CreateMediaInput]] = None


@strawberry.input
class CreateSuperAdminInput:
    name: str
    mobilenumber: str
    email: Optional[str] = None
    password: Optional[str] = None
    media: Optional[list[CreateMediaInput]] = None



@strawberry.input
class UpdateUserInput:
    name: Optional[str] = None
    mobilenumber: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    media: Optional[list[CreateMediaInput]] = None


@strawberry.input
class CreateUserAddressInput:
    address_line_1: str = strawberry.field(name="addressLine1")
    address_line_2: Optional[str] = strawberry.field(default=None, name="addressLine2")
    landmark: Optional[str] = strawberry.field(default=None)
    pincode: str
    state: str
    district: str
    customer_name: str = strawberry.field(name="customerName")
    phone_number: str = strawberry.field(name="phoneNumber")
    is_primary: bool = strawberry.field(default=False, name="isPrimary")
    lat_long: Optional[str] = strawberry.field(default=None, name="latLong")
    third_party_app_address: Optional[str] = strawberry.field(default=None, name="thirdPartyAppAddress")


@strawberry.input
class UpdateUserAddressInput:
    address_line_1: Optional[str] = strawberry.field(default=None, name="addressLine1")
    address_line_2: Optional[str] = strawberry.field(default=None, name="addressLine2")
    landmark: Optional[str] = strawberry.field(default=None)
    pincode: Optional[str] = strawberry.field(default=None)
    state: Optional[str] = strawberry.field(default=None)
    district: Optional[str] = strawberry.field(default=None)
    customer_name: Optional[str] = strawberry.field(default=None, name="customerName")
    phone_number: Optional[str] = strawberry.field(default=None, name="phoneNumber")
    is_primary: Optional[bool] = strawberry.field(default=None, name="isPrimary")
    lat_long: Optional[str] = strawberry.field(default=None, name="latLong")
    third_party_app_address: Optional[str] = strawberry.field(default=None, name="thirdPartyAppAddress")



@strawberry.type
class UserQuery:
    @strawberry.field
    async def me(self, info: strawberry.Info) -> UserType:
        """Fetch details of the currently authenticated user."""
        user = info.context.user
        if not user:
            raise UnauthorizedError("Not authenticated. Please login first.")
        return UserType(user)

    @strawberry.field
    async def my_addresses(self, info: strawberry.Info) -> list[UserAddressType]:
        """Fetch all addresses of the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_addresses = await user_service.get_user_addresses(db, current_user.id)
        return [UserAddressType(addr) for addr in db_addresses]

    @strawberry.field
    async def address(self, info: strawberry.Info, id: uuid.UUID) -> Optional[UserAddressType]:
        """Fetch a single address of the currently authenticated user by ID."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_address = await user_service.get_user_address_by_id(db, current_user.id, id)
        return UserAddressType(db_address) if db_address else None

    @strawberry.field
    async def my_cart(self, info: strawberry.Info) -> UserCartType:
        """Fetch details of the currently authenticated user's cart (creates one if none exists)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_cart = await user_service.get_or_create_cart(db, tenant_id, current_user.id)
        return UserCartType(db_cart)

    @strawberry.field
    async def total_users(self, info: strawberry.Info) -> int:
        """Fetch total number of users for the admin's tenant (or overall if Super Admin)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to view total users.")
        
        db = info.context.db
        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id
            if tenant_id:
                return await user_service.get_total_users_by_tenant(db, tenant_id)
            else:
                from sqlalchemy import func, select
                from app.users.models import User
                res = await db.execute(select(func.count(User.id)))
                return res.scalar_one() or 0
        else:
            tenant_id = current_user.tenant_id
            if not tenant_id:
                raise ValidationError("Tenant ID context is missing.")
            return await user_service.get_total_users_by_tenant(db, tenant_id)

    @strawberry.field
    async def tenant_users(self, info: strawberry.Info) -> list[UserType]:
        """Fetch users for the admin's tenant (or all users if Super Admin)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to view tenant users.")
        
        db = info.context.db
        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id
            if tenant_id:
                db_users = await user_service.get_users_by_tenant(db, tenant_id)
            else:
                db_users = await user_service.get_all_users(db)
        else:
            # TENANT_ADMIN strictly sees their own tenant's users
            tenant_id = current_user.tenant_id
            if not tenant_id:
                raise ValidationError("Tenant ID context is missing.")
            db_users = await user_service.get_users_by_tenant(db, tenant_id)

        return [UserType(user) for user in db_users]

    @strawberry.field
    async def admin_user_cart(self, info: strawberry.Info, user_id: uuid.UUID) -> Optional[UserCartType]:
        """Fetch details of a specific user's cart (Admin only)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to view other users' carts.")
            
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
            
        db = info.context.db
        from app.users.models import UserCart
        from sqlalchemy.future import select
        # First verify the user belongs to the tenant if TENANT_ADMIN
        from app.users.models import User
        if current_user.role == "TENANT_ADMIN":
            stmt_user = select(User).where(User.id == user_id, User.tenant_id == tenant_id)
            res_user = await db.execute(stmt_user)
            if not res_user.scalar_one_or_none():
                raise UnauthorizedError("User not found in your tenant.")
                
        stmt = select(UserCart).where(UserCart.user_id == user_id)
        res = await db.execute(stmt)
        db_cart = res.scalar_one_or_none()
        return UserCartType(db_cart) if db_cart else None




@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def update_me(self, info: strawberry.Info, input: UpdateUserInput) -> UserType:
        """Update the currently authenticated user's details and media."""
        db = info.context.db
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        if not current_user:
            raise UnauthorizedError("Not authenticated. Please login first.")

        if not tenant_id:
            tenant_id = current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        kwargs = {}
        for field in ["name", "mobilenumber", "email", "password"]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        db_user = await user_service.update_user(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            **kwargs
        )

        if input.media is not None:
            # Delete existing media
            from app.media.models import Media
            from sqlalchemy import delete
            await db.execute(
                delete(Media).where(
                    (Media.tenant_id == tenant_id) &
                    (Media.entity_name == "user") &
                    (Media.entity_id == current_user.id)
                )
            )
            # Create new media entries
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                    db=db,
                    tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="user",
                    entity_id=current_user.id,
                    user_id=current_user.id
                )

        return UserType(db_user)
    @strawberry.mutation
    async def create_user(self, info: strawberry.Info, input: CreateUserInput) -> UserType:
        """Create a user inside the current active tenant (Requires Admin permissions)."""
        db = info.context.db
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        # 1. Authorize: must be authenticated as tenant admin or super admin
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to create users.")

        # Prevent TENANT_ADMIN from creating a SUPER_ADMIN user
        if current_user.role != "SUPER_ADMIN" and input.role.value == "SUPER_ADMIN":
            raise UnauthorizedError("Only SUPER_ADMIN can create or assign the SUPER_ADMIN role.")

        # 2. Use user's tenant if tenant context not set
        if not tenant_id:
            tenant_id = current_user.tenant_id

        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_user = await user_service.create_user(
            db=db,
            name=input.name,
            mobilenumber=input.mobilenumber,
            email=input.email,
            password=input.password,
            role=input.role.value,
            tenant_id=tenant_id
        )

        if input.media:
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                    db=db,
                    tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="user",
                    entity_id=db_user.id,
                    user_id=current_user.id
                )

        return UserType(db_user)

    @strawberry.mutation
    async def create_system_super_admin(self, info: strawberry.Info, input: CreateSuperAdminInput) -> UserType:
        """Create a system-level SUPER_ADMIN (Requires SUPER_ADMIN permissions)."""
        db = info.context.db
        current_user = info.context.user

        # 1. Authorize: must be authenticated as super admin
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        
        if current_user.role != "SUPER_ADMIN":
            raise UnauthorizedError("Only a SUPER_ADMIN can create another SUPER_ADMIN.")

        # 2. Fetch or create a default system tenant
        from sqlalchemy.future import select
        from app.tenants.models import Tenant
        
        stmt_tenant = select(Tenant).limit(1)
        res_tenant = await db.execute(stmt_tenant)
        tenant = res_tenant.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(business_name="System Default Tenant")
            db.add(tenant)
            await db.flush()
            
        tenant_id = tenant.id

        db_user = await user_service.create_user(
            db=db,
            name=input.name,
            mobilenumber=input.mobilenumber,
            email=input.email,
            password=input.password,
            role="SUPER_ADMIN",
            tenant_id=tenant_id
        )

        if input.media:
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                    db=db,
                    tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="user",
                    entity_id=db_user.id,
                    user_id=current_user.id
                )

        return UserType(db_user)

    @strawberry.mutation
    async def update_user(self, info: strawberry.Info, id: uuid.UUID, input: UpdateUserInput) -> UserType:
        """Update an existing user's details and media (Requires Admin permissions)."""
        db = info.context.db
        current_user = info.context.user
        tenant_id = info.context.tenant_id

        # 1. Authorize: must be authenticated as tenant admin or super admin
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to update users.")

        # 2. Use user's tenant if tenant context not set
        if not tenant_id:
            tenant_id = current_user.tenant_id

        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        # Extract only provided input fields for user update
        kwargs = {}
        for field in ["name", "mobilenumber", "email", "password"]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        if input.role is not None:
            kwargs["role"] = input.role.value
        if input.status is not None:
            kwargs["status"] = input.status.value

        db_user = await user_service.update_user(
            db=db,
            tenant_id=tenant_id,
            user_id=id,
            **kwargs
        )

        
        if input.media is not None:
            # Delete existing media
            from app.media.models import Media
            from sqlalchemy import delete
            await db.execute(
                delete(Media).where(
                    (Media.tenant_id == tenant_id) &
                    (Media.entity_name == "user") &
                    (Media.entity_id == id)
                )
            )
            # Create new media entries
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                    db=db,
                    tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="user",
                    entity_id=db_user.id,
                    user_id=current_user.id
                )

        return UserType(db_user)

    @strawberry.mutation
    async def create_user_address(self, info: strawberry.Info, input: CreateUserAddressInput) -> UserAddressType:
        """Create a new address for the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db

        db_address = await user_service.create_user_address(
            db=db,
            user_id=current_user.id,
            address_line_1=input.address_line_1,
            address_line_2=input.address_line_2,
            landmark=input.landmark,
            pincode=input.pincode,
            state=input.state,
            district=input.district,
            customer_name=input.customer_name,
            phone_number=input.phone_number,
            is_primary=input.is_primary,
            lat_long=input.lat_long,
            third_party_app_address=input.third_party_app_address
        )
        return UserAddressType(db_address)

    @strawberry.mutation
    async def update_user_address(self, info: strawberry.Info, id: uuid.UUID, input: UpdateUserAddressInput) -> UserAddressType:
        """Update an existing address for the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db

        # Extract only provided input fields
        kwargs = {}
        for field in [
            "address_line_1", "address_line_2", "landmark", "pincode",
            "state", "district", "customer_name", "phone_number",
            "is_primary", "lat_long", "third_party_app_address"
        ]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        db_address = await user_service.update_user_address(
            db=db,
            user_id=current_user.id,
            address_id=id,
            **kwargs
        )
        return UserAddressType(db_address)

    @strawberry.mutation
    async def delete_user_address(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete an address for the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db

        return await user_service.delete_user_address(db, current_user.id, id)

    @strawberry.mutation
    async def add_to_cart(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        quantity: int = 1
    ) -> UserCartType:
        """Add a product to the authenticated user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_cart = await user_service.add_to_cart(db, tenant_id, current_user.id, product_id, quantity)
        return UserCartType(db_cart)

    @strawberry.mutation
    async def update_cart_item(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        quantity: int
    ) -> UserCartType:
        """Update a cart item's quantity."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_cart = await user_service.update_cart_item(db, tenant_id, current_user.id, product_id, quantity)
        return UserCartType(db_cart)

    @strawberry.mutation
    async def remove_from_cart(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID
    ) -> UserCartType:
        """Remove a product from the user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_cart = await user_service.remove_from_cart(db, tenant_id, current_user.id, product_id)
        return UserCartType(db_cart)

    @strawberry.mutation
    async def clear_cart(
        self,
        info: strawberry.Info
    ) -> UserCartType:
        """Clear all items from the user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_cart = await user_service.clear_cart(db, tenant_id, current_user.id)
        return UserCartType(db_cart)

    @strawberry.mutation
    async def apply_coupon_to_cart(self, info: strawberry.Info, code: str) -> UserCartType:
        """Apply a coupon code directly to the authenticated user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from app.promotions.services import coupon_service
        cart = await coupon_service.apply_coupon_to_cart(db, tenant_id, current_user.id, code)
        return UserCartType(cart)

    @strawberry.mutation
    async def remove_coupon_from_cart(self, info: strawberry.Info, code: str) -> UserCartType:
        """Remove a coupon code from the authenticated user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from app.promotions.services import coupon_service
        cart = await coupon_service.remove_coupon_from_cart(db, tenant_id, current_user.id, code)
        return UserCartType(cart)

    @strawberry.mutation
    async def clear_coupons_from_cart(self, info: strawberry.Info) -> UserCartType:
        """Clear all coupons from the authenticated user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from app.promotions.services import coupon_service
        cart = await coupon_service.clear_coupons_from_cart(db, tenant_id, current_user.id)
        return UserCartType(cart)

    @strawberry.mutation
    async def request_forgot_password_otp(self, info: strawberry.Info, mobilenumber: str) -> bool:
        """Trigger an SMS OTP for password reset."""
        db = info.context.db
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
            
        return await user_service.request_forgot_password_otp(db, tenant_id, mobilenumber)

    @strawberry.mutation
    async def reset_password_with_otp(self, info: strawberry.Info, mobilenumber: str, otp: str, new_password: str) -> bool:
        """Verify OTP and update user's password."""
        db = info.context.db
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
            
        return await user_service.reset_password_with_otp(db, tenant_id, mobilenumber, otp, new_password)
