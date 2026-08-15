import uuid
from datetime import datetime
from typing import Optional, List, Annotated
import strawberry

from app.products.pricing.models import (
    PricingType as DBPricingType,
    ProductPrice as DBProductPrice,
    ProductPricingRule as DBProductPricingRule
)
from app.products.pricing.services import pricing_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class PricingTypeType:
    """GraphQL representation of a Pricing Type."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    type: str
    created_at: datetime
    updated_at: datetime

    def __init__(self, db_pt: DBPricingType):
        self.id = db_pt.id
        self.tenant_id = db_pt.tenant_id
        self.type = db_pt.type
        self.created_at = db_pt.created_at
        self.updated_at = db_pt.updated_at


@strawberry.type
class ProductPriceType:
    """GraphQL representation of a Product Price mapping."""
    id: uuid.UUID
    product_id: uuid.UUID = strawberry.field(name="productId")
    pricing_type_id: uuid.UUID = strawberry.field(name="pricingTypeId")
    price: float
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def pricing_type(self, info: strawberry.Info) -> PricingTypeType:
        """Resolve the associated pricing type details."""
        db = info.context.db
        
        # Resolve by ID directly to avoid context mismatch issues (e.g. Admin viewing cross-tenant data)
        from sqlalchemy.future import select
        from app.products.pricing.models import PricingType
        
        stmt = select(PricingType).where(PricingType.id == self.pricing_type_id)
        res = await db.execute(stmt)
        db_pt = res.scalar_one_or_none()
        
        if not db_pt:
            raise ValidationError("Pricing type not found.")
        return PricingTypeType(db_pt)

    def __init__(self, db_price: DBProductPrice):
        self.id = db_price.id
        self.product_id = db_price.product_id
        self.pricing_type_id = db_price.pricing_type_id
        self.price = float(db_price.price)
        self.created_at = db_price.created_at
        self.updated_at = db_price.updated_at


@strawberry.type
class ProductPricingRuleType:
    id: uuid.UUID
    product_id: uuid.UUID = strawberry.field(name="productId")
    name: str
    priority: int
    rule_type: str = strawberry.field(name="ruleType")
    value: float
    min_quantity: Optional[int] = strawberry.field(name="minQuantity")
    max_quantity: Optional[int] = strawberry.field(name="maxQuantity")
    location_id: Optional[uuid.UUID] = strawberry.field(name="locationId")
    pincode: Optional[str]
    start_time: Optional[datetime] = strawberry.field(name="startTime")
    end_time: Optional[datetime] = strawberry.field(name="endTime")
    day_of_week: Optional[int] = strawberry.field(name="dayOfWeek")
    start_hour: Optional[int] = strawberry.field(name="startHour")
    end_hour: Optional[int] = strawberry.field(name="endHour")
    min_stock: Optional[int] = strawberry.field(name="minStock")
    max_stock: Optional[int] = strawberry.field(name="maxStock")
    pricing_type_id: Optional[uuid.UUID] = strawberry.field(name="pricingTypeId")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def pricing_type(self, info: strawberry.Info) -> Optional[PricingTypeType]:
        if not self.pricing_type_id:
            return None
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_pt = await pricing_service.get_pricing_type_by_id(db, tenant_id, self.pricing_type_id)
        return PricingTypeType(db_pt) if db_pt else None

    def __init__(self, db_rule: DBProductPricingRule):
        self.id = db_rule.id
        self.product_id = db_rule.product_id
        self.name = db_rule.name
        self.priority = db_rule.priority
        self.rule_type = db_rule.rule_type
        self.value = float(db_rule.value)
        self.min_quantity = db_rule.min_quantity
        self.max_quantity = db_rule.max_quantity
        self.location_id = db_rule.location_id
        self.pincode = db_rule.pincode
        self.start_time = db_rule.start_time
        self.end_time = db_rule.end_time
        self.day_of_week = db_rule.day_of_week
        self.start_hour = db_rule.start_hour
        self.end_hour = db_rule.end_hour
        self.min_stock = db_rule.min_stock
        self.max_stock = db_rule.max_stock
        self.pricing_type_id = db_rule.pricing_type_id
        self.created_at = db_rule.created_at
        self.updated_at = db_rule.updated_at


@strawberry.input
class CreatePricingTypeInput:
    type: str


@strawberry.input
class UpdatePricingTypeInput:
    type: str


@strawberry.input
class SetProductPriceInput:
    product_id: uuid.UUID = strawberry.field(name="productId")
    pricing_type_id: uuid.UUID = strawberry.field(name="pricingTypeId")
    price: float


@strawberry.input
class CreateProductPricingRuleInput:
    product_id: uuid.UUID = strawberry.field(name="productId")
    name: str
    priority: int = 0
    rule_type: str = strawberry.field(name="ruleType")
    value: float
    min_quantity: Optional[int] = strawberry.field(default=None, name="minQuantity")
    max_quantity: Optional[int] = strawberry.field(default=None, name="maxQuantity")
    location_id: Optional[uuid.UUID] = strawberry.field(default=None, name="locationId")
    pincode: Optional[str] = strawberry.field(default=None)
    start_time: Optional[datetime] = strawberry.field(default=None, name="startTime")
    end_time: Optional[datetime] = strawberry.field(default=None, name="endTime")
    day_of_week: Optional[int] = strawberry.field(default=None, name="dayOfWeek")
    start_hour: Optional[int] = strawberry.field(default=None, name="startHour")
    end_hour: Optional[int] = strawberry.field(default=None, name="endHour")
    min_stock: Optional[int] = strawberry.field(default=None, name="minStock")
    max_stock: Optional[int] = strawberry.field(default=None, name="maxStock")
    pricing_type_id: Optional[uuid.UUID] = strawberry.field(default=None, name="pricingTypeId")


@strawberry.type
class PricingQuery:
    @strawberry.field
    async def pricing_types(self, info: strawberry.Info) -> List[PricingTypeType]:
        """Fetch all pricing types configured under the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_pts = await pricing_service.get_pricing_types(db, tenant_id)
        return [PricingTypeType(pt) for pt in db_pts]

    @strawberry.field
    async def product_prices(self, info: strawberry.Info, product_id: uuid.UUID) -> List[ProductPriceType]:
        """Fetch all price mappings for a specific product scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_prices = await pricing_service.get_product_prices(db, tenant_id, product_id)
        return [ProductPriceType(p) for p in db_prices]

    @strawberry.field
    async def product_pricing_rules(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID
    ) -> List[ProductPricingRuleType]:
        """Fetch all pricing rules for a product (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing rules.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        from sqlalchemy.future import select
        stmt = select(DBProductPricingRule).where(
            (DBProductPricingRule.tenant_id == tenant_id) &
            (DBProductPricingRule.product_id == product_id)
        ).order_by(DBProductPricingRule.priority.desc())
        res = await db.execute(stmt)
        rules = res.scalars().all()
        return [ProductPricingRuleType(r) for r in rules]


@strawberry.type
class PricingMutation:
    @strawberry.mutation
    async def create_pricing_type(self, info: strawberry.Info, input: CreatePricingTypeInput) -> PricingTypeType:
        """Create a new pricing type scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing configs.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_pt = await pricing_service.create_pricing_type(
            db=db,
            tenant_id=tenant_id,
            type_name=input.type,
            user_id=current_user.id
        )
        return PricingTypeType(db_pt)

    @strawberry.mutation
    async def update_pricing_type(self, info: strawberry.Info, id: uuid.UUID, input: UpdatePricingTypeInput) -> PricingTypeType:
        """Update an existing pricing type scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing configs.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_pt = await pricing_service.update_pricing_type(
            db=db,
            tenant_id=tenant_id,
            pricing_type_id=id,
            type_name=input.type,
            user_id=current_user.id
        )
        return PricingTypeType(db_pt)

    @strawberry.mutation
    async def delete_pricing_type(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete a pricing type scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing configs.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await pricing_service.delete_pricing_type(
            db=db,
            tenant_id=tenant_id,
            pricing_type_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def set_product_price(self, info: strawberry.Info, input: SetProductPriceInput) -> ProductPriceType:
        """Set or update a specific price mapping for a product (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product prices.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_price = await pricing_service.set_product_price(
            db=db,
            tenant_id=tenant_id,
            product_id=input.product_id,
            pricing_type_id=input.pricing_type_id,
            price_value=input.price,
            user_id=current_user.id
        )
        return ProductPriceType(db_price)

    @strawberry.mutation
    async def delete_product_price(self, info: strawberry.Info, product_id: uuid.UUID, pricing_type_id: uuid.UUID) -> bool:
        """Delete a product price mapping (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product prices.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await pricing_service.delete_product_price(
            db=db,
            tenant_id=tenant_id,
            product_id=product_id,
            pricing_type_id=pricing_type_id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def create_product_pricing_rule(
        self,
        info: strawberry.Info,
        input: CreateProductPricingRuleInput
    ) -> ProductPricingRuleType:
        """Create a dynamic pricing rule (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing rules.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db_rule = await pricing_service.create_pricing_rule(
            db=db,
            tenant_id=tenant_id,
            product_id=input.product_id,
            name=input.name,
            priority=input.priority,
            rule_type=input.rule_type,
            value=input.value,
            min_quantity=input.min_quantity,
            max_quantity=input.max_quantity,
            location_id=input.location_id,
            pincode=input.pincode,
            start_time=input.start_time,
            end_time=input.end_time,
            day_of_week=input.day_of_week,
            start_hour=input.start_hour,
            end_hour=input.end_hour,
            min_stock=input.min_stock,
            max_stock=input.max_stock,
            pricing_type_id=input.pricing_type_id
        )
        return ProductPricingRuleType(db_rule)

    @strawberry.mutation
    async def delete_product_pricing_rule(
        self,
        info: strawberry.Info,
        id: uuid.UUID
    ) -> bool:
        """Delete a dynamic pricing rule (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage pricing rules.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        return await pricing_service.delete_pricing_rule(db, tenant_id, id)
