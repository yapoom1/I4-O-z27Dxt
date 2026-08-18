import uuid
from datetime import datetime
from typing import Optional, List, Annotated
from enum import Enum
import strawberry

from app.products.products.mongo_models import (
    Product as DBProduct,
    Attribute as DBAttribute,
    AttributeValueModel as DBAttributeValue,
    ProductAttributeModel as DBProductAttributeValue,
    ProductGroup as DBProductGroup,
    ProductGroupLinkModel as DBProductGroupLink,
    ProductStockModel as DBProductStock,
    ProductShippingModel as DBProductShipping
)
from sqlalchemy.future import select
from app.products.products.services import product_service
from app.utils.exceptions import UnauthorizedError, ValidationError
from app.media.graphql import MediaType, CreateMediaInput

@strawberry.enum
class ProductTypeEnum(Enum):
    GOODS = "GOODS"
    SERVICE = "SERVICE"
    OTHERS = "OTHERS"


@strawberry.type
class AttributeType:
    """GraphQL representation of an Attribute."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    name: str
    display_name: str = strawberry.field(name="displayName")
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def values(self, info: strawberry.Info) -> List["AttributeValueType"]:
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        db_vals = await product_service.get_attribute_values(tenant_id, self.id)
        return [AttributeValueType(val) for val in db_vals]

    def __init__(self, db_attr: DBAttribute):
        self.id = db_attr.id
        self.tenant_id = db_attr.tenant_id
        self.name = db_attr.name
        self.display_name = db_attr.display_name
        self.created_at = db_attr.created_at


@strawberry.type
class AttributeValueType:
    """GraphQL representation of an Attribute Value."""
    id: uuid.UUID
    attribute_id: uuid.UUID = strawberry.field(name="attributeId")
    value: str
    hex_code: Optional[str] = strawberry.field(name="hexCode")
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def attribute(self, info: strawberry.Info) -> AttributeType:
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_attr = await product_service.get_attribute_by_id(db, tenant_id, self.attribute_id)
        if not db_attr:
            raise ValidationError("Attribute not found.")
        return AttributeType(db_attr)

    def __init__(self, db_val: DBAttributeValue):
        self.id = db_val.id
        self.attribute_id = db_val.attribute_id
        self.value = db_val.value
        self.hex_code = db_val.hex_code
        self.created_at = db_val.created_at


@strawberry.type
class ProductAttributeValueType:
    """GraphQL representation of a Product Attribute Value mapping."""
    id: uuid.UUID
    product_id: uuid.UUID = strawberry.field(name="productId")
    attribute_value_id: uuid.UUID = strawberry.field(name="attributeValueId")
    pricing_type_id: Optional[uuid.UUID] = strawberry.field(name="pricingTypeId")
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def attribute_value(self, info: strawberry.Info) -> AttributeValueType:
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_val = await product_service.get_attribute_value_by_id(db, tenant_id, self.attribute_value_id)
        if not db_val:
            raise ValidationError("Attribute value not found.")
        return AttributeValueType(db_val)

    @strawberry.field
    async def pricing_type(self, info: strawberry.Info) -> Optional[Annotated["PricingTypeType", strawberry.lazy("app.products.pricing.graphql")]]:
        if not self.pricing_type_id:
            return None
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        from app.products.pricing.services import pricing_service
        from app.products.pricing.graphql import PricingTypeType
        db_pt = await pricing_service.get_pricing_type_by_id(db, tenant_id, self.pricing_type_id)
        return PricingTypeType(db_pt) if db_pt else None

    def __init__(self, db_pav: DBProductAttributeValue):
        self.id = getattr(db_pav, "id", uuid.uuid4())
        self.product_id = getattr(db_pav, "product_id", uuid.uuid4())
        self.attribute_value_id = getattr(db_pav, "attribute_value_id", uuid.uuid4())
        self.pricing_type_id = db_pav.pricing_type_id
        self.created_at = getattr(db_pav, "created_at", datetime.utcnow())


@strawberry.type
class ProductGroupType:
    """GraphQL representation of a Product Group."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    name: str
    description: Optional[str]
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def products(self, info: strawberry.Info) -> List["ProductType"]:
        tenant_id = info.context.tenant_id or self.tenant_id
        db_products = await DBProduct.find(
            {"groups.group_id": self.id, "tenant_id": tenant_id}
        ).sort("-created_at").to_list()
        return [ProductType(p) for p in db_products]

    def __init__(self, db_group: DBProductGroup):
        self.id = db_group.id
        self.tenant_id = db_group.tenant_id
        self.name = db_group.name
        self.description = db_group.description
        self.created_at = db_group.created_at
        self.updated_at = db_group.updated_at


@strawberry.type
class ProductGroupLinkType:
    """GraphQL representation of a Product-to-Group mapping."""
    id: uuid.UUID
    product_id: uuid.UUID = strawberry.field(name="productId")
    group_id: uuid.UUID = strawberry.field(name="groupId")
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def group(self, info: strawberry.Info) -> ProductGroupType:
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_group = await product_service.get_product_group_by_id(tenant_id, self.group_id)
        if not db_group:
            raise ValidationError("Product group not found.")
        return ProductGroupType(db_group)

    def __init__(self, db_link: DBProductGroupLink):
        self.id = getattr(db_link, "id", uuid.uuid4())
        self.product_id = getattr(db_link, "product_id", uuid.uuid4())
        self.group_id = getattr(db_link, "group_id", uuid.uuid4())
        self.created_at = getattr(db_link, "created_at", datetime.utcnow())


@strawberry.type
class ProductStockType:
    """GraphQL representation of Product Stock."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    product_id: uuid.UUID = strawberry.field(name="productId")
    stock: int
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    def __init__(self, db_stock: DBProductStock):
        self.id = getattr(db_stock, "id", uuid.uuid4())
        self.tenant_id = getattr(db_stock, "tenant_id", uuid.uuid4())
        self.product_id = getattr(db_stock, "product_id", uuid.uuid4())
        self.stock = db_stock.stock if hasattr(db_stock, "stock") else 0
        self.created_at = getattr(db_stock, "created_at", datetime.utcnow())
        self.updated_at = getattr(db_stock, "updated_at", datetime.utcnow())


@strawberry.type
class ProductShippingType:
    """GraphQL representation of Product Shipping dimensions."""
    weight: float
    length: float
    width: float
    height: float

    def __init__(self, db_shipping: DBProductShipping):
        self.weight = getattr(db_shipping, "weight", 0.5)
        self.length = getattr(db_shipping, "length", 10.0)
        self.width = getattr(db_shipping, "width", 10.0)
        self.height = getattr(db_shipping, "height", 10.0)


@strawberry.type
class ProductType:
    """GraphQL representation of a Product."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = strawberry.field(name="parentId")
    title: str
    subtitle: Optional[str]
    description: Optional[str]
    description_long: Optional[str] = strawberry.field(name="descriptionLong")
    sku: Optional[str]
    product_type: ProductTypeEnum = strawberry.field(name="productType")
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(name="thumbnailMediaId")
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def shipping_dimensions(self) -> Optional[ProductShippingType]:
        """Resolve shipping dimensions."""
        return ProductShippingType(self._shipping_data) if self._shipping_data else None

    @strawberry.field
    async def parent(self, info: strawberry.Info) -> Optional["ProductType"]:
        """Resolve parent product relation."""
        if not self.parent_id:
            return None
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        db_parent = await product_service.get_product_by_id(tenant_id, self.parent_id)
        return ProductType(db_parent) if db_parent else None

    @strawberry.field
    async def children(self, info: strawberry.Info) -> List["ProductType"]:
        """Resolve child products (variants)."""
        tenant_id = info.context.tenant_id or self.tenant_id
        db_children = await DBProduct.find(
            {"parent_id": self.id, "tenant_id": tenant_id}
        ).sort("-created_at").to_list()
        return [ProductType(c) for c in db_children]

    @strawberry.field
    async def price(self, info: strawberry.Info) -> Optional[float]:
        """Resolve default 'selling_price' directly on Product using DataLoader."""
        if not info.context.dataloaders:
            return None
        val = await info.context.dataloaders.selling_price_loader.load(self.id)
        return val

    @strawberry.field
    async def effective_price(
        self,
        info: strawberry.Info,
        quantity: int = 1,
        location_id: Optional[uuid.UUID] = None,
        pincode: Optional[str] = None,
        pricing_type: Optional[str] = None
    ) -> float:
        """Resolve dynamic effective price based on context parameters using DataLoader."""
        if not info.context.dataloaders:
            return 0.0

        # We need the product stock level using DataLoader
        stock = self._stock_data.stock if self._stock_data else 0
        
        # Build key for effective_price loader
        key = (self.id, quantity, location_id, pincode, pricing_type, stock)
        return await info.context.dataloaders.effective_price_loader.load(key)

    @strawberry.field
    async def prices(self, info: strawberry.Info) -> List[Annotated["ProductPriceType", strawberry.lazy("app.products.pricing.graphql")]]:
        """Resolve all product price mappings."""
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        from app.products.pricing.services import pricing_service
        from app.products.pricing.graphql import ProductPriceType
        db_prices = await pricing_service.get_product_prices(db, tenant_id, self.id)
        return [ProductPriceType(p) for p in db_prices]

    @strawberry.field
    async def thumbnail(self, info: strawberry.Info) -> Optional[MediaType]:
        """Resolve the thumbnail media details using DataLoader."""
        if not self.thumbnail_media_id or not info.context.dataloaders:
            return None
        db_media = await info.context.dataloaders.media_loader.load(self.thumbnail_media_id)
        return MediaType(db_media) if db_media else None

    @strawberry.field
    async def media(self, info: strawberry.Info) -> List[MediaType]:
        """Resolve all associated media files for this product."""
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        from app.media.services import media_service
        db_media_list = await media_service.get_media_list(db, tenant_id, entity_name="product", entity_id=self.id)
        return [MediaType(m) for m in db_media_list]

    @strawberry.field
    async def categories(self, info: strawberry.Info) -> List[Annotated["CategoryType", strawberry.lazy("app.products.categories.graphql")]]:
        """Resolve all associated categories for this product using DataLoader."""
        if not info.context.dataloaders:
            return []
        db_categories = await info.context.dataloaders.category_loader.load_many(self._category_ids)
        from app.products.categories.graphql import CategoryType
        return [CategoryType(c) for c in db_categories if c]

    @strawberry.field
    async def attributes(self, info: strawberry.Info) -> List[ProductAttributeValueType]:
        """Resolve all product attribute mappings."""
        return [ProductAttributeValueType(pav) for pav in self._attributes_data]

    @strawberry.field
    async def groups(self, info: strawberry.Info) -> List[ProductGroupLinkType]:
        """Resolve all product group mappings."""
        return [ProductGroupLinkType(link) for link in self._groups_data]

    @strawberry.field
    async def related_products(self, info: strawberry.Info) -> List["ProductType"]:
        """Resolve other products sharing at least one product group with this product."""
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        db_related = await product_service.get_related_products(tenant_id, self.id)
        return [ProductType(p) for p in db_related]

    @strawberry.field
    async def stock(self, info: strawberry.Info) -> int:
        """Resolve current product stock level using DataLoader."""
        return self._stock_data.stock if self._stock_data else 0

    @strawberry.field
    async def reviews(self, info: strawberry.Info) -> List[Annotated["ProductReviewType", strawberry.lazy("app.reviews.graphql")]]:
        """Resolve approved reviews for this product."""
        db = info.context.db
        from app.reviews.services import reviews_service
        from app.reviews.graphql import ProductReviewType
        db_reviews = await reviews_service.get_product_reviews(db, self.id)
        return [ProductReviewType(r) for r in db_reviews]

    @strawberry.field
    async def pricing_rules(self, info: strawberry.Info) -> List[Annotated["ProductPricingRuleType", strawberry.lazy("app.products.pricing.graphql")]]:
        """Resolve pricing rules for this product."""
        db = info.context.db
        from app.products.pricing.models import ProductPricingRule
        from app.products.pricing.graphql import ProductPricingRuleType
        stmt = select(ProductPricingRule).where(
            (ProductPricingRule.product_id == self.id) &
            (ProductPricingRule.tenant_id == (info.context.tenant_id or self.tenant_id))
        ).order_by(ProductPricingRule.priority.desc())
        res = await db.execute(stmt)
        db_rules = res.scalars().all()
        return [ProductPricingRuleType(r) for r in db_rules]

    def __init__(self, db_product: DBProduct):
        self.id = db_product.id
        self.tenant_id = db_product.tenant_id
        self.parent_id = db_product.parent_id
        self.title = db_product.title
        self.subtitle = db_product.subtitle
        self.description = db_product.description
        self.description_long = db_product.description_long
        self.sku = db_product.sku
        self.product_type = ProductTypeEnum(db_product.product_type)
        self.thumbnail_media_id = db_product.thumbnail_media_id
        self.created_at = db_product.created_at
        self.updated_at = db_product.updated_at
        
        self._stock_data = db_product.stock
        self._shipping_data = db_product.shipping
        self._attributes_data = db_product.attributes
        self._groups_data = db_product.groups
        self._category_ids = db_product.category_ids


@strawberry.input
class CreateAttributeInput:
    name: str
    display_name: str = strawberry.field(name="displayName")


@strawberry.input
class UpdateAttributeInput:
    name: str
    display_name: str = strawberry.field(name="displayName")


@strawberry.input
class CreateAttributeValueInput:
    attribute_id: uuid.UUID = strawberry.field(name="attributeId")
    value: str
    hex_code: Optional[str] = strawberry.field(default=None, name="hexCode")


@strawberry.input
class UpdateAttributeValueInput:
    value: Optional[str] = strawberry.field(default=None)
    hex_code: Optional[str] = strawberry.field(default=None, name="hexCode")


@strawberry.input
class CreateProductGroupInput:
    name: str
    description: Optional[str] = strawberry.field(default=None)


@strawberry.input
class UpdateProductGroupInput:
    name: Optional[str] = strawberry.field(default=None)
    description: Optional[str] = strawberry.field(default=None)


@strawberry.input
class ShippingDimensionsInput:
    weight: Optional[float] = strawberry.field(default=None) # Mandatory: Must be provided > 0
    length: Optional[float] = strawberry.field(default=10.0)
    width: Optional[float] = strawberry.field(default=10.0)
    height: Optional[float] = strawberry.field(default=10.0)

@strawberry.input
class CreateProductInput:
    title: str
    product_type: ProductTypeEnum = strawberry.field(name="productType")
    subtitle: Optional[str] = strawberry.field(default=None)
    description: Optional[str] = strawberry.field(default=None)
    description_long: Optional[str] = strawberry.field(default=None, name="descriptionLong")
    sku: Optional[str] = strawberry.field(default=None)
    parent_id: Optional[uuid.UUID] = strawberry.field(default=None, name="parentId")
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(default=None, name="thumbnailMediaId")
    media: Optional[List[CreateMediaInput]] = None
    shipping_dimensions: Optional[ShippingDimensionsInput] = strawberry.field(default=None, name="shippingDimensions")


@strawberry.input
class UpdateProductInput:
    title: Optional[str] = strawberry.field(default=None)
    product_type: Optional[ProductTypeEnum] = strawberry.field(default=None, name="productType")
    subtitle: Optional[str] = strawberry.field(default=None)
    description: Optional[str] = strawberry.field(default=None)
    description_long: Optional[str] = strawberry.field(default=None, name="descriptionLong")
    sku: Optional[str] = strawberry.field(default=None)
    parent_id: Optional[uuid.UUID] = strawberry.field(default=None, name="parentId")
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(default=None, name="thumbnailMediaId")
    media: Optional[List[CreateMediaInput]] = None
    shipping_dimensions: Optional[ShippingDimensionsInput] = strawberry.field(default=None, name="shippingDimensions")


@strawberry.type
class ProductQuery:
    @strawberry.field
    async def products(
        self,
        info: strawberry.Info,
        product_type: Optional[ProductTypeEnum] = None,
        search: Optional[str] = None
    ) -> List[ProductType]:
        """Fetch products scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        db = info.context.db
        pt_val = product_type.value if product_type else None
        db_products = await product_service.get_products(
                        tenant_id=tenant_id,
            product_type=pt_val,
            search=search
        )
        return [ProductType(p) for p in db_products]

    @strawberry.field
    async def product(self, info: strawberry.Info, id: uuid.UUID) -> Optional[ProductType]:
        """Fetch a single product by ID scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        db = info.context.db
        db_product = await product_service.get_product_by_id(tenant_id, id)
        return ProductType(db_product) if db_product else None

    @strawberry.field
    async def attributes(self, info: strawberry.Info) -> List[AttributeType]:
        """Fetch all attributes configured under the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_attrs = await product_service.get_attributes(tenant_id)
        return [AttributeType(a) for a in db_attrs]

    @strawberry.field
    async def attribute(self, info: strawberry.Info, id: uuid.UUID) -> Optional[AttributeType]:
        """Fetch a single attribute by ID scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_attr = await product_service.get_attribute_by_id(tenant_id, id)
        return AttributeType(db_attr) if db_attr else None

    @strawberry.field
    async def attribute_values(self, info: strawberry.Info, attribute_id: uuid.UUID) -> List[AttributeValueType]:
        """Fetch all option values for a specific attribute scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_vals = await product_service.get_attribute_values(tenant_id, attribute_id)
        return [AttributeValueType(val) for val in db_vals]

    @strawberry.field
    async def product_groups(self, info: strawberry.Info) -> List[ProductGroupType]:
        """Fetch all product groups scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_groups = await product_service.get_product_groups(tenant_id)
        return [ProductGroupType(g) for g in db_groups]

    @strawberry.field
    async def product_group(self, info: strawberry.Info, id: uuid.UUID) -> Optional[ProductGroupType]:
        """Fetch a single product group by ID scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_group = await product_service.get_product_group_by_id(tenant_id, id)
        return ProductGroupType(db_group) if db_group else None


@strawberry.type
class ProductMutation:
    @strawberry.mutation
    async def create_product(self, info: strawberry.Info, input: CreateProductInput) -> ProductType:
        """Create a new product under the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage products.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_product = await product_service.create_product(
                        tenant_id=tenant_id,
            title=input.title,
            product_type=input.product_type.value,
            subtitle=input.subtitle,
            description=input.description,
            description_long=input.description_long,
            sku=input.sku,
            parent_id=input.parent_id,
            thumbnail_media_id=input.thumbnail_media_id,
            shipping_dimensions=input.shipping_dimensions.__dict__ if input.shipping_dimensions else None,
            user_id=current_user.id
        )

        if input.media:
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                                        tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="product",
                    entity_id=db_product.id,
                    user_id=current_user.id
                )

        return ProductType(db_product)

    @strawberry.mutation
    async def update_product(self, info: strawberry.Info, id: uuid.UUID, input: UpdateProductInput) -> ProductType:
        """Update an existing product scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage products.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        kwargs = {}
        for field in [
            "title", "subtitle", "description", "description_long",
            "sku", "parent_id", "thumbnail_media_id"
        ]:
            val = getattr(input, field)
            if val is not None:
                kwargs[field] = val

        if input.product_type is not None:
            kwargs["product_type"] = input.product_type.value

        if input.shipping_dimensions is not None:
            kwargs["shipping_dimensions"] = input.shipping_dimensions.__dict__

        db = info.context.db
        db_product = await product_service.update_product(
                        tenant_id=tenant_id,
            product_id=id,
            user_id=current_user.id,
            **kwargs
        )

        if input.media is not None:
            from app.media.models import Media
            from sqlalchemy import delete
            await db.execute(
                delete(Media).where(
                    (Media.tenant_id == tenant_id) &
                    (Media.entity_name == "product") &
                    (Media.entity_id == id)
                )
            )
            from app.media.services import media_service
            for med_input in input.media:
                await media_service.create_media(
                                        tenant_id=tenant_id,
                    file_path=med_input.file_path,
                    media_url=med_input.media_url,
                    media_type=med_input.media_type.value,
                    file_extension=med_input.file_extension,
                    alt_text=med_input.alt_text,
                    meta_attributes=med_input.meta_attributes,
                    entity_name="product",
                    entity_id=db_product.id,
                    user_id=current_user.id
                )

        return ProductType(db_product)

    @strawberry.mutation
    async def delete_product(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete a product scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage products.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.delete_product(
                        tenant_id=tenant_id,
            product_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def create_attribute(self, info: strawberry.Info, input: CreateAttributeInput) -> AttributeType:
        """Create a new attribute under the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attributes.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_attr = await product_service.create_attribute(
                        tenant_id=tenant_id,
            name=input.name,
            display_name=input.display_name,
            user_id=current_user.id
        )
        return AttributeType(db_attr)

    @strawberry.mutation
    async def update_attribute(self, info: strawberry.Info, id: uuid.UUID, input: UpdateAttributeInput) -> AttributeType:
        """Update an existing attribute scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attributes.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_attr = await product_service.update_attribute(
                        tenant_id=tenant_id,
            attribute_id=id,
            name=input.name,
            display_name=input.display_name,
            user_id=current_user.id
        )
        return AttributeType(db_attr)

    @strawberry.mutation
    async def delete_attribute(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete an attribute scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attributes.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.delete_attribute(
                        tenant_id=tenant_id,
            attribute_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def create_attribute_value(self, info: strawberry.Info, input: CreateAttributeValueInput) -> AttributeValueType:
        """Create a new attribute value scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attribute values.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_val = await product_service.create_attribute_value(
                        tenant_id=tenant_id,
            attribute_id=input.attribute_id,
            value=input.value,
            hex_code=input.hex_code,
            user_id=current_user.id
        )
        return AttributeValueType(db_val)

    @strawberry.mutation
    async def update_attribute_value(self, info: strawberry.Info, id: uuid.UUID, input: UpdateAttributeValueInput) -> AttributeValueType:
        """Update an existing attribute value scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attribute values.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_val = await product_service.update_attribute_value(
                        tenant_id=tenant_id,
            attribute_value_id=id,
            value=input.value,
            hex_code=input.hex_code,
            user_id=current_user.id
        )
        return AttributeValueType(db_val)

    @strawberry.mutation
    async def delete_attribute_value(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete an attribute value scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage attribute values.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.delete_attribute_value(
                        tenant_id=tenant_id,
            attribute_value_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def assign_attribute_value_to_product(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        pricing_type_id: Optional[uuid.UUID] = None
    ) -> ProductAttributeValueType:
        """Link an attribute value option to a product (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product attributes.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_pav = await product_service.assign_attribute_value_to_product(
                        tenant_id=tenant_id,
            product_id=product_id,
            attribute_value_id=attribute_value_id,
            pricing_type_id=pricing_type_id,
            user_id=current_user.id
        )
        return ProductAttributeValueType(db_pav)

    @strawberry.mutation
    async def remove_attribute_value_from_product(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        attribute_value_id: uuid.UUID
    ) -> bool:
        """Remove an attribute value link from a product (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product attributes.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.remove_attribute_value_from_product(
                        tenant_id=tenant_id,
            product_id=product_id,
            attribute_value_id=attribute_value_id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def create_product_group(self, info: strawberry.Info, input: CreateProductGroupInput) -> ProductGroupType:
        """Create a new product group scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product groups.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_group = await product_service.create_product_group(
                        tenant_id=tenant_id,
            name=input.name,
            description=input.description,
            user_id=current_user.id
        )
        return ProductGroupType(db_group)

    @strawberry.mutation
    async def update_product_group(self, info: strawberry.Info, id: uuid.UUID, input: UpdateProductGroupInput) -> ProductGroupType:
        """Update an existing product group scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product groups.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_group = await product_service.update_product_group(
                        tenant_id=tenant_id,
            group_id=id,
            name=input.name,
            description=input.description,
            user_id=current_user.id
        )
        return ProductGroupType(db_group)

    @strawberry.mutation
    async def delete_product_group(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete a product group scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product groups.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.delete_product_group(
                        tenant_id=tenant_id,
            group_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def link_product_to_group(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        group_id: uuid.UUID
    ) -> ProductGroupLinkType:
        """Link a product to a product group (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product groups.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_link = await product_service.link_product_to_group(
                        tenant_id=tenant_id,
            product_id=product_id,
            group_id=group_id,
            user_id=current_user.id
        )
        return ProductGroupLinkType(db_link)

    @strawberry.mutation
    async def unlink_product_from_group(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        group_id: uuid.UUID
    ) -> bool:
        """Unlink a product from a product group (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product groups.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await product_service.unlink_product_from_group(
                        tenant_id=tenant_id,
            product_id=product_id,
            group_id=group_id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def update_product_stock(
        self,
        info: strawberry.Info,
        product_id: uuid.UUID,
        stock: int
    ) -> ProductStockType:
        """Create or update product stock level (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage stock.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_stock = await product_service.update_product_stock(
                        tenant_id=tenant_id,
            product_id=product_id,
            stock_value=stock,
            user_id=current_user.id
        )
        return ProductStockType(db_stock)
