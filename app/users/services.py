import uuid
from typing import Optional
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.users.models import User, UserAddress, UserCart, CartItem
from app.products.products.services import ProductService
from app.tenants.models import Tenant
from app.utils.audit import log_audit_event
from app.auth.services import auth_service, sms_service
from app.utils.exceptions import TenantNotFoundError, ValidationError

class UserService:
    """Service handling PostgreSQL and MongoDB operations for users and their addresses."""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        name: str,
        mobilenumber: str,
        email: Optional[str],
        password: Optional[str],
        role: str,
        tenant_id: uuid.UUID
    ) -> User:
        """Create a new User within a tenant."""
        # 1. Verify tenant exists
        stmt_tenant = select(Tenant).where(Tenant.id == tenant_id)
        res_tenant = await db.execute(stmt_tenant)
        if not res_tenant.scalar_one_or_none():
            raise TenantNotFoundError(f"Tenant {tenant_id} not found.")

        # 2. Check if credentials already taken inside this tenant
        stmt_user = select(User).where(
            (User.tenant_id == tenant_id) &
            ((User.mobilenumber == mobilenumber) | (User.email == email))
        )
        res_user = await db.execute(stmt_user)
        if res_user.scalar_one_or_none():
            raise ValidationError("A user with this email or mobile number already exists in this tenant.")

        hashed_password = auth_service.hash_password(password) if password else None
        user = User(
            name=name,
            mobilenumber=mobilenumber,
            email=email,
            password=hashed_password,
            role=role,
            tenant_id=tenant_id,
            status="ACTIVE"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Log to MongoDB safely
        await log_audit_event(
            action="USER_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user.id),
            details={"name": name, "email": email, "role": role}
        )

        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[User]:
        """Fetch user by ID scoped to the tenant."""
        stmt = select(User).where(
            (User.id == user_id) &
            (User.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_total_users_by_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Fetch total count of users within a tenant."""
        from sqlalchemy import func
        stmt = select(func.count(User.id)).where(User.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one() or 0

    @staticmethod
    async def get_users_by_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
        """Fetch all users within a tenant."""
        stmt = select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_users(db: AsyncSession) -> list[User]:
        """Fetch all users across all tenants (Super Admin only)."""
        stmt = select(User).order_by(User.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_addresses(db: AsyncSession, user_id: uuid.UUID) -> list[UserAddress]:
        """Fetch all addresses for a user."""
        stmt = select(UserAddress).where(UserAddress.user_id == user_id).order_by(UserAddress.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_address_by_id(db: AsyncSession, user_id: uuid.UUID, address_id: uuid.UUID) -> Optional[UserAddress]:
        """Fetch a single address by user and address IDs."""
        stmt = select(UserAddress).where(
            (UserAddress.id == address_id) &
            (UserAddress.user_id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user_address(
        db: AsyncSession,
        user_id: uuid.UUID,
        address_line_1: str,
        address_line_2: Optional[str],
        landmark: Optional[str],
        pincode: str,
        state: str,
        district: str,
        customer_name: str,
        phone_number: str,
        is_primary: bool,
        lat_long: Optional[str] = None,
        third_party_app_address: Optional[str] = None
    ) -> UserAddress:
        """Create a new address for a user. Marks others non-primary if is_primary is True."""
        if is_primary:
            await db.execute(
                update(UserAddress)
                .where(UserAddress.user_id == user_id)
                .values(is_primary=False)
            )

        db_address = UserAddress(
            user_id=user_id,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            landmark=landmark,
            pincode=pincode,
            state=state,
            district=district,
            customer_name=customer_name,
            phone_number=phone_number,
            is_primary=is_primary,
            lat_long=lat_long,
            third_party_app_address=third_party_app_address
        )
        db.add(db_address)
        await db.commit()
        await db.refresh(db_address)
        return db_address

    @staticmethod
    async def update_user_address(
        db: AsyncSession,
        user_id: uuid.UUID,
        address_id: uuid.UUID,
        **kwargs
    ) -> UserAddress:
        """Update an existing address. Marks others non-primary if is_primary is True."""
        stmt = select(UserAddress).where(
            (UserAddress.id == address_id) &
            (UserAddress.user_id == user_id)
        )
        result = await db.execute(stmt)
        db_address = result.scalar_one_or_none()
        if not db_address:
            raise ValidationError("Address not found or does not belong to the user.")

        if kwargs.get("is_primary") is True:
            await db.execute(
                update(UserAddress)
                .where(UserAddress.user_id == user_id)
                .values(is_primary=False)
            )

        for field, value in kwargs.items():
            if value is not None:
                setattr(db_address, field, value)

        await db.commit()
        await db.refresh(db_address)
        return db_address

    @staticmethod
    async def delete_user_address(db: AsyncSession, user_id: uuid.UUID, address_id: uuid.UUID) -> bool:
        """Delete an address for a user."""
        stmt = select(UserAddress).where(
            (UserAddress.id == address_id) &
            (UserAddress.user_id == user_id)
        )
        result = await db.execute(stmt)
        db_address = result.scalar_one_or_none()
        if not db_address:
            raise ValidationError("Address not found or does not belong to the user.")

        await db.delete(db_address)
        await db.commit()
        return True

    @staticmethod
    async def update_user(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs
    ) -> User:
        """Update an existing User within a tenant."""
        # 1. Fetch user
        user = await UserService.get_user_by_id(db, user_id, tenant_id)
        if not user:
            raise ValidationError("User not found or belongs to another tenant.")

        # 2. Check if email/mobile is being changed and if it is already taken inside this tenant
        email = kwargs.get("email")
        mobilenumber = kwargs.get("mobilenumber")
        if email or mobilenumber:
            stmt = select(User).where(
                (User.tenant_id == tenant_id) &
                (User.id != user_id)
            )
            if email and mobilenumber:
                stmt = stmt.where((User.mobilenumber == mobilenumber) | (User.email == email))
            elif email:
                stmt = stmt.where(User.email == email)
            else:
                stmt = stmt.where(User.mobilenumber == mobilenumber)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                raise ValidationError("A user with this email or mobile number already exists in this tenant.")

        # Hash password if provided
        if "password" in kwargs:
            pwd = kwargs["password"]
            if pwd:
                kwargs["password"] = auth_service.hash_password(pwd)
            else:
                kwargs.pop("password")
        
        # 3. Apply updates
        for field, value in kwargs.items():
            setattr(user, field, value)

        print("kwargs =", kwargs)
        print("before =", user.name, user.email, user.mobilenumber)
        await db.commit()
        await db.refresh(user)
        print("after =", user.name, user.email, user.mobilenumber)

        # 4. Log to MongoDB safely
        await log_audit_event(
            action="USER_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            details={"updated_fields": list(kwargs.keys())}
        )

        return user

    @staticmethod
    async def request_forgot_password_otp(db: AsyncSession, tenant_id: uuid.UUID, mobilenumber: str) -> bool:
        """Send OTP to mobile number if user exists."""
        stmt = select(User).where(
            (User.tenant_id == tenant_id) &
            (User.mobilenumber == mobilenumber)
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise ValidationError("User not found.")
            
        await sms_service.send_otp(mobilenumber)
        return True

    @staticmethod
    async def reset_password_with_otp(db: AsyncSession, tenant_id: uuid.UUID, mobilenumber: str, otp: str, new_password: str) -> bool:
        """Verify OTP and update user's password."""
        # 1. Verify OTP
        is_valid = await sms_service.verify_otp(mobilenumber, otp)
        if not is_valid:
            raise ValidationError("Invalid or expired OTP.")
            
        # 2. Get user
        stmt = select(User).where(
            (User.tenant_id == tenant_id) &
            (User.mobilenumber == mobilenumber)
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise ValidationError("User not found.")
            
        # 3. Update password
        user.password = auth_service.hash_password(new_password)
        await db.commit()
        
        # 4. Log to MongoDB safely
        await log_audit_event(
            action="USER_PASSWORD_RESET",
            tenant_id=str(tenant_id),
            user_id=str(user.id),
            details={"method": "sms_otp"}
        )
        
        return True

    @staticmethod
    async def get_or_create_cart(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> UserCart:
        """Fetch or create a UserCart record."""
        # Check if the user exists and belongs to the active tenant
        stmt_user = select(User).where((User.id == user_id) & (User.tenant_id == tenant_id))
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        if not user:
            raise ValidationError("User not found or belongs to another tenant.")
        
        # Now find or create UserCart
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id).options(selectinload(UserCart.items))
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            cart = UserCart(user_id=user_id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
        return cart

    @staticmethod
    async def add_to_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int = 1
    ) -> UserCart:
        """Add item. Enforce product exists under tenant. If item already exists, increment quantity."""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive to add to cart.")
        
        # Enforce user belongs to active tenant
        cart = await UserService.get_or_create_cart(db, tenant_id, user_id)
        
        # Enforce product exists under active tenant
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")
        
        # Check if item already in cart
        stmt_item = select(CartItem).where((CartItem.cart_id == cart.id) & (CartItem.product_id == product_id))
        res_item = await db.execute(stmt_item)
        item = res_item.scalar_one_or_none()
        if item:
            item.quantity += quantity
        else:
            item = CartItem(cart_id=cart.id, user_id=user_id, product_id=product_id, quantity=quantity)
            db.add(item)
            
        await db.commit()
        await db.refresh(cart)
        return cart

    @staticmethod
    async def update_cart_item(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int
    ) -> UserCart:
        """Set exact quantity. If quantity is 0 or negative, delete the item."""
        cart = await UserService.get_or_create_cart(db, tenant_id, user_id)
        
        # Check if product exists in cart
        stmt_item = select(CartItem).where((CartItem.cart_id == cart.id) & (CartItem.product_id == product_id))
        res_item = await db.execute(stmt_item)
        item = res_item.scalar_one_or_none()
        
        if quantity <= 0:
            if item:
                await db.delete(item)
                await db.commit()
        else:
            # If not in cart but product belongs to tenant, we can create it
            if not item:
                product = await ProductService.get_product_by_id(tenant_id, product_id)
                if not product:
                    raise ValidationError("Product not found or belongs to another tenant.")
                
                item = CartItem(cart_id=cart.id, user_id=user_id, product_id=product_id, quantity=quantity)
                db.add(item)
            else:
                item.quantity = quantity
            await db.commit()
            
        await db.refresh(cart)
        return cart

    @staticmethod
    async def remove_from_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> UserCart:
        """Delete specific cart item."""
        cart = await UserService.get_or_create_cart(db, tenant_id, user_id)
        
        stmt_item = select(CartItem).where((CartItem.cart_id == cart.id) & (CartItem.product_id == product_id))
        res_item = await db.execute(stmt_item)
        item = res_item.scalar_one_or_none()
        
        if item:
            await db.delete(item)
            await db.commit()
            
        await db.refresh(cart)
        return cart

    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> UserCart:
        """Delete all items in the user's cart."""
        cart = await UserService.get_or_create_cart(db, tenant_id, user_id)
        
        from sqlalchemy import delete
        stmt = delete(CartItem).where(CartItem.cart_id == cart.id)
        await db.execute(stmt)
        await db.commit()
        await db.refresh(cart)
        return cart

user_service = UserService()
