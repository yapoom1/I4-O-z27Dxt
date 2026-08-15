import uuid
from datetime import datetime
from typing import Optional, List, Annotated
import strawberry

from app.products.categories.mongo_models import Category as DBCategory
from app.products.products.mongo_models import Product as DBProduct
from app.products.categories.services import category_service
from app.utils.exceptions import UnauthorizedError, ValidationError
from app.media.graphql import MediaType, CreateMediaInput

@strawberry.type
class CategoryType:
    """GraphQL representation of a Category."""
    id: uuid.UUID
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    parent_id: Optional[uuid.UUID] = strawberry.field(name="parentId")
    title: str
    subtitle: Optional[str]
    description: Optional[str]
    description_long: Optional[str] = strawberry.field(name="descriptionLong")
    sku: Optional[str]
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(name="thumbnailMediaId")
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def parent(self, info: strawberry.Info) -> Optional["CategoryType"]:
        """Resolve parent category relation."""
        if not self.parent_id:
            return None
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        db_parent = await category_service.get_category_by_id(tenant_id, self.parent_id)
        return CategoryType(db_parent) if db_parent else None

    @strawberry.field
    async def children(self, info: strawberry.Info) -> List["CategoryType"]:
        """Resolve child categories."""
        tenant_id = info.context.tenant_id or self.tenant_id
        db_children = await DBCategory.find(
            {"parent_id": self.id, "tenant_id": tenant_id}
        ).sort("-created_at").to_list()
        return [CategoryType(c) for c in db_children]

    @strawberry.field
    async def products(self, info: strawberry.Info) -> List[Annotated["ProductType", strawberry.lazy("app.products.products.graphql")]]:
        """Resolve all products associated with this category."""
        tenant_id = info.context.tenant_id or self.tenant_id
        db_products = await DBProduct.find(
            {"category_ids": self.id, "tenant_id": tenant_id}
        ).sort("-created_at").to_list()
        from app.products.products.graphql import ProductType
        return [ProductType(p) for p in db_products]

    @strawberry.field
    async def thumbnail(self, info: strawberry.Info) -> Optional[MediaType]:
        """Resolve the thumbnail media details."""
        if not self.thumbnail_media_id:
            return None
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        from app.media.services import media_service
        db_media = await media_service.get_media_by_id(db, tenant_id, self.thumbnail_media_id)
        return MediaType(db_media) if db_media else None

    @strawberry.field
    async def media(self, info: strawberry.Info) -> List[MediaType]:
        """Resolve all associated media files for this category."""
        db = info.context.db
        tenant_id = info.context.tenant_id or self.tenant_id
        from app.media.services import media_service
        db_media_list = await media_service.get_media_list(db, tenant_id, entity_name="category", entity_id=self.id)
        return [MediaType(m) for m in db_media_list]

    def __init__(self, db_category: DBCategory):
        self.id = db_category.id
        self.tenant_id = db_category.tenant_id
        self.parent_id = db_category.parent_id
        self.title = db_category.title
        self.subtitle = db_category.subtitle
        self.description = db_category.description
        self.description_long = db_category.description_long
        self.sku = db_category.sku
        self.thumbnail_media_id = db_category.thumbnail_media_id
        self.created_at = db_category.created_at
        self.updated_at = db_category.updated_at


@strawberry.input
class CreateCategoryInput:
    title: str
    parent_id: Optional[uuid.UUID] = strawberry.field(default=None, name="parentId")
    subtitle: Optional[str] = strawberry.field(default=None)
    description: Optional[str] = strawberry.field(default=None)
    description_long: Optional[str] = strawberry.field(default=None, name="descriptionLong")
    sku: Optional[str] = strawberry.field(default=None)
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(default=None, name="thumbnailMediaId")
    media: Optional[List[CreateMediaInput]] = None


@strawberry.input
class UpdateCategoryInput:
    title: Optional[str] = strawberry.field(default=None)
    parent_id: Optional[uuid.UUID] = strawberry.field(default=None, name="parentId")
    subtitle: Optional[str] = strawberry.field(default=None)
    description: Optional[str] = strawberry.field(default=None)
    description_long: Optional[str] = strawberry.field(default=None, name="descriptionLong")
    sku: Optional[str] = strawberry.field(default=None)
    thumbnail_media_id: Optional[uuid.UUID] = strawberry.field(default=None, name="thumbnailMediaId")
    media: Optional[List[CreateMediaInput]] = None


@strawberry.type
class CategoryQuery:
    @strawberry.field
    async def categories(self, info: strawberry.Info, search: Optional[str] = None) -> List[CategoryType]:
        """Fetch categories scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_categories = await category_service.get_categories(tenant_id, search=search)
        return [CategoryType(c) for c in db_categories]

    @strawberry.field
    async def category(self, info: strawberry.Info, id: uuid.UUID) -> Optional[CategoryType]:
        """Fetch a single category by ID scoped to the current tenant."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db = info.context.db
        db_category = await category_service.get_category_by_id(tenant_id, id)
        return CategoryType(db_category) if db_category else None


@strawberry.type
class CategoryMutation:
    @strawberry.mutation
    async def create_category(self, info: strawberry.Info, input: CreateCategoryInput) -> CategoryType:
        """Create a new category (Requires Admin permissions)."""
        print(f"DEBUG: create_category called with title={input.title}, sku={input.sku}")
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage categories.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_category = await category_service.create_category(
                        tenant_id=tenant_id,
            title=input.title,
            parent_id=input.parent_id,
            subtitle=input.subtitle,
            description=input.description,
            description_long=input.description_long,
            sku=input.sku,
            thumbnail_media_id=input.thumbnail_media_id,
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
                    entity_name="category",
                    entity_id=db_category.id,
                    user_id=current_user.id
                )

        return CategoryType(db_category)

    @strawberry.mutation
    async def update_category(self, info: strawberry.Info, id: uuid.UUID, input: UpdateCategoryInput) -> CategoryType:
        """Update an existing category scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage categories.")

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

        db = info.context.db
        db_category = await category_service.update_category(
                        tenant_id=tenant_id,
            category_id=id,
            user_id=current_user.id,
            **kwargs
        )

        if input.media is not None:
            from app.media.models import Media
            from sqlalchemy import delete
            await db.execute(
                delete(Media).where(
                    (Media.tenant_id == tenant_id) &
                    (Media.entity_name == "category") &
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
                    entity_name="category",
                    entity_id=db_category.id,
                    user_id=current_user.id
                )

        return CategoryType(db_category)

    @strawberry.mutation
    async def delete_category(self, info: strawberry.Info, id: uuid.UUID) -> bool:
        """Delete a category scoped to the current tenant (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage categories.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        return await category_service.delete_category(
                        tenant_id=tenant_id,
            category_id=id,
            user_id=current_user.id
        )

    @strawberry.mutation
    async def set_product_categories(self, info: strawberry.Info, product_id: uuid.UUID, category_ids: List[uuid.UUID]) -> List[CategoryType]:
        """Replace all categories associated with a product (Requires Admin permissions)."""
        current_user = info.context.user

        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to manage product categories.")

        if current_user.role == "SUPER_ADMIN":
            tenant_id = info.context.tenant_id or current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
            
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        db = info.context.db
        db_categories = await category_service.set_product_categories(
                        tenant_id=tenant_id,
            product_id=product_id,
            category_ids=category_ids,
            user_id=current_user.id
        )
        return [CategoryType(c) for c in db_categories]
