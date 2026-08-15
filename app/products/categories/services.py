import uuid
from typing import Optional, List
from datetime import datetime

from app.products.categories.mongo_models import Category
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class CategoryService:
    """Service handling MongoDB operations for Product Categories."""

    @staticmethod
    async def get_categories(
        tenant_id: uuid.UUID,
        search: Optional[str] = None
    ) -> List[Category]:
        """Fetch all categories scoped to a tenant, with optional search filtering."""
        query = {"tenant_id": tenant_id}
        if search:
            search_pattern = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"title": search_pattern},
                {"subtitle": search_pattern},
                {"sku": search_pattern}
            ]
        
        return await Category.find(query).sort("-created_at").to_list()

    @staticmethod
    async def get_category_by_id(
        tenant_id: uuid.UUID,
        category_id: uuid.UUID
    ) -> Optional[Category]:
        """Fetch a single category by ID scoped to a tenant."""
        return await Category.find_one({"_id": category_id, "tenant_id": tenant_id})

    @staticmethod
    async def create_category(
        tenant_id: uuid.UUID,
        title: str,
        parent_id: Optional[uuid.UUID] = None,
        subtitle: Optional[str] = None,
        description: Optional[str] = None,
        description_long: Optional[str] = None,
        sku: Optional[str] = None,
        thumbnail_media_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Category:
        """Create a new Category under a tenant."""
        if sku:
            existing = await Category.find_one({"tenant_id": tenant_id, "sku": sku})
            if existing:
                raise ValidationError(f"A category with SKU '{sku}' already exists under this tenant.")

        if parent_id:
            parent = await CategoryService.get_category_by_id(tenant_id, parent_id)
            if not parent:
                raise ValidationError(f"Parent category {parent_id} not found or belongs to another tenant.")

        category = Category(
            tenant_id=tenant_id,
            parent_id=parent_id,
            title=title,
            subtitle=subtitle,
            description=description,
            description_long=description_long,
            sku=sku,
            thumbnail_media_id=thumbnail_media_id
        )
        await category.insert()

        await log_audit_event(
            action="CATEGORY_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "category_id": str(category.id),
                "title": title,
                "sku": sku
            }
        )

        return category

    @staticmethod
    async def update_category(
        tenant_id: uuid.UUID,
        category_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Category:
        """Update an existing category."""
        category = await CategoryService.get_category_by_id(tenant_id, category_id)
        if not category:
            raise ValidationError("Category not found or belongs to another tenant.")

        sku = kwargs.get("sku")
        if sku and sku != category.sku:
            existing = await Category.find_one({
                "tenant_id": tenant_id,
                "sku": sku,
                "_id": {"$ne": category_id}
            })
            if existing:
                raise ValidationError(f"A category with SKU '{sku}' already exists under this tenant.")

        parent_id = kwargs.get("parent_id")
        if parent_id is not None:
            if parent_id == category_id:
                raise ValidationError("A category cannot be its own parent.")
            parent = await CategoryService.get_category_by_id(tenant_id, parent_id)
            if not parent:
                raise ValidationError(f"Parent category {parent_id} not found or belongs to another tenant.")

        for field, value in kwargs.items():
            if hasattr(category, field):
                setattr(category, field, value)

        category.updated_at = datetime.utcnow()
        await category.save()

        await log_audit_event(
            action="CATEGORY_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "category_id": str(category_id),
                "updated_fields": list(kwargs.keys())
            }
        )

        return category

    @staticmethod
    async def delete_category(
        tenant_id: uuid.UUID,
        category_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a category from the database."""
        category = await CategoryService.get_category_by_id(tenant_id, category_id)
        if not category:
            raise ValidationError("Category not found or belongs to another tenant.")

        await category.delete()

        await log_audit_event(
            action="CATEGORY_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={"category_id": str(category_id)}
        )

        return True

    @staticmethod
    async def set_product_categories(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        category_ids: List[uuid.UUID],
        user_id: Optional[uuid.UUID] = None
    ) -> List[Category]:
        """Replace all categories associated with a product."""
        # Using MongoDB, categories for a product are stored on the Product document!
        from app.products.products.mongo_models import Product
        
        product = await Product.find_one({"_id": product_id, "tenant_id": tenant_id})
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        # Verify all categories exist under tenant
        categories = []
        for cat_id in category_ids:
            category = await CategoryService.get_category_by_id(tenant_id, cat_id)
            if not category:
                raise ValidationError(f"Category {cat_id} not found or belongs to another tenant.")
            categories.append(category)

        # Replace mappings on the Product document
        product.category_ids = [c.id for c in categories]
        product.updated_at = datetime.utcnow()
        await product.save()

        await log_audit_event(
            action="PRODUCT_CATEGORIES_SET",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "product_id": str(product_id),
                "category_ids": [str(c.id) for c in categories]
            }
        )

        return categories

category_service = CategoryService()
