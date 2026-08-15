import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.products.products.mongo_models import (
    Product, Attribute, AttributeValueModel, ProductAttributeModel,
    ProductGroup, ProductGroupLinkModel, ProductStockModel
)
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class ProductService:
    """Service handling MongoDB operations for Products, attributes, groups, and stock."""

    @staticmethod
    async def get_products(
        tenant_id: uuid.UUID,
        product_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Product]:
        """Fetch all products scoped to a tenant, with optional type and search filtering."""
        query = {"tenant_id": tenant_id}
        if product_type:
            query["product_type"] = product_type
            
        if search:
            search_pattern = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"title": search_pattern},
                {"subtitle": search_pattern},
                {"sku": search_pattern}
            ]
            
        return await Product.find(query).sort("-created_at").to_list()

    @staticmethod
    async def get_product_by_id(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> Optional[Product]:
        """Fetch a single product by ID scoped to a tenant."""
        return await Product.find_one({"_id": product_id, "tenant_id": tenant_id})

    @staticmethod
    async def get_product_by_ids(
        tenant_id: uuid.UUID,
        product_ids: List[uuid.UUID]
    ) -> List[Product]:
        """Fetch multiple products by their IDs scoped to a tenant."""
        if not product_ids:
            return []
        
        products = await Product.find({"_id": {"$in": product_ids}, "tenant_id": tenant_id}).to_list()
        prod_map = {p.id: p for p in products}
        return [prod_map[pid] for pid in product_ids if pid in prod_map]

    @staticmethod
    async def get_products_by_category(
        tenant_id: uuid.UUID,
        category_id: uuid.UUID,
        limit: Optional[int] = None
    ) -> List[Product]:
        """Fetch products mapped to a specific category, scoped to a tenant."""
        query = Product.find({"category_ids": category_id, "tenant_id": tenant_id}).sort("-created_at")
        if limit is not None:
            query = query.limit(limit)
        return await query.to_list()

    @staticmethod
    async def get_best_sellers(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 10
    ) -> List[Product]:
        """Fetch best-selling products based on quantity sold in orders."""
        from app.orders.models import OrderItem, Order
        stmt = (
            select(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_sold"))
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.tenant_id == tenant_id)
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        product_ids = [row[0] for row in result.all()]
        
        products = await ProductService.get_product_by_ids(tenant_id, product_ids)
        
        # Fallback to newest products if we have fewer best sellers than the limit
        if len(products) < limit:
            exclude_ids = [p.id for p in products]
            fallback_limit = limit - len(products)
            
            query = {"tenant_id": tenant_id}
            if exclude_ids:
                query["_id"] = {"$nin": exclude_ids}
                
            fallback_products = await Product.find(query).sort("-created_at").limit(fallback_limit).to_list()
            products.extend(fallback_products)
            
        return products

    @staticmethod
    async def get_new_arrivals(
        tenant_id: uuid.UUID,
        limit: int = 10
    ) -> List[Product]:
        """Fetch newest products scoped to a tenant."""
        return await Product.find({"tenant_id": tenant_id}).sort("-created_at").limit(limit).to_list()

    @staticmethod
    async def create_product(
        tenant_id: uuid.UUID,
        title: str,
        product_type: str,
        subtitle: Optional[str] = None,
        description: Optional[str] = None,
        description_long: Optional[str] = None,
        sku: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
        thumbnail_media_id: Optional[uuid.UUID] = None,
        shipping_dimensions: Optional[dict] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Product:
        """Create a new Product under a tenant."""
        if sku:
            existing = await Product.find_one({"tenant_id": tenant_id, "sku": sku})
            if existing:
                raise ValidationError(f"A product with SKU '{sku}' already exists under this tenant.")

        if parent_id:
            parent = await ProductService.get_product_by_id(tenant_id, parent_id)
            if not parent:
                raise ValidationError(f"Parent product {parent_id} not found or belongs to another tenant.")

        from app.products.products.mongo_models import ProductShippingModel
        shipping = ProductShippingModel(**shipping_dimensions) if shipping_dimensions else None

        product = Product(
            tenant_id=tenant_id,
            parent_id=parent_id,
            title=title,
            subtitle=subtitle,
            description=description,
            description_long=description_long,
            sku=sku,
            product_type=product_type,
            thumbnail_media_id=thumbnail_media_id,
            shipping=shipping
        )
        await product.insert()

        await log_audit_event(
            action="PRODUCT_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "product_id": str(product.id),
                "title": title,
                "sku": sku,
                "product_type": product_type
            }
        )

        return product

    @staticmethod
    async def update_product(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Product:
        """Update an existing product."""
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        sku = kwargs.get("sku")
        if sku and sku != product.sku:
            existing = await Product.find_one({
                "tenant_id": tenant_id,
                "sku": sku,
                "_id": {"$ne": product_id}
            })
            if existing:
                raise ValidationError(f"A product with SKU '{sku}' already exists under this tenant.")

        parent_id = kwargs.get("parent_id")
        if parent_id is not None:
            if parent_id == product_id:
                raise ValidationError("A product cannot be its own parent.")
            parent = await ProductService.get_product_by_id(tenant_id, parent_id)
            if not parent:
                raise ValidationError(f"Parent product {parent_id} not found or belongs to another tenant.")

        if "shipping_dimensions" in kwargs:
            ship_dims = kwargs.pop("shipping_dimensions")
            if ship_dims:
                from app.products.products.mongo_models import ProductShippingModel
                product.shipping = ProductShippingModel(**ship_dims)

        for field, value in kwargs.items():
            if hasattr(product, field):
                setattr(product, field, value)

        product.updated_at = datetime.utcnow()
        await product.save()

        await log_audit_event(
            action="PRODUCT_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "product_id": str(product_id),
                "updated_fields": list(kwargs.keys())
            }
        )

        return product

    @staticmethod
    async def delete_product(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a product from the database."""
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        await product.delete()

        await log_audit_event(
            action="PRODUCT_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={"product_id": str(product_id)}
        )

        return True

    # --- Attribute Management ---

    @staticmethod
    async def get_attributes(tenant_id: uuid.UUID) -> List[Attribute]:
        """Fetch all attributes configured under a tenant."""
        return await Attribute.find({"tenant_id": tenant_id}).sort("name").to_list()

    @staticmethod
    async def get_attribute_by_id(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID
    ) -> Optional[Attribute]:
        """Fetch a single attribute by ID scoped to a tenant."""
        return await Attribute.find_one({"_id": attribute_id, "tenant_id": tenant_id})

    @staticmethod
    async def create_attribute(
        tenant_id: uuid.UUID,
        name: str,
        display_name: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Attribute:
        """Create a new attribute (e.g. color, size) under a tenant."""
        name = name.strip().lower()
        display_name = display_name.strip()
        if not name or not display_name:
            raise ValidationError("Attribute name and display name cannot be empty.")

        existing = await Attribute.find_one({"tenant_id": tenant_id, "name": name})
        if existing:
            raise ValidationError(f"Attribute '{name}' already exists under this tenant.")

        attribute = Attribute(
            tenant_id=tenant_id,
            name=name,
            display_name=display_name
        )
        await attribute.insert()

        await log_audit_event(
            action="ATTRIBUTE_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "attribute_id": str(attribute.id),
                "name": name,
                "display_name": display_name
            }
        )

        return attribute

    @staticmethod
    async def update_attribute(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID,
        name: str,
        display_name: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Attribute:
        """Update an existing attribute."""
        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found or belongs to another tenant.")

        name = name.strip().lower()
        display_name = display_name.strip()
        if not name or not display_name:
            raise ValidationError("Attribute name and display name cannot be empty.")

        if name != attribute.name:
            existing = await Attribute.find_one({
                "tenant_id": tenant_id,
                "name": name,
                "_id": {"$ne": attribute_id}
            })
            if existing:
                raise ValidationError(f"Attribute '{name}' already exists under this tenant.")

        attribute.name = name
        attribute.display_name = display_name
        await attribute.save()

        await log_audit_event(
            action="ATTRIBUTE_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "attribute_id": str(attribute_id),
                "name": name,
                "display_name": display_name
            }
        )

        return attribute

    @staticmethod
    async def delete_attribute(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete an attribute scoped to a tenant."""
        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found or belongs to another tenant.")

        await attribute.delete()

        await log_audit_event(
            action="ATTRIBUTE_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={"attribute_id": str(attribute_id)}
        )

        return True

    # --- Attribute Value Management ---
    
    @staticmethod
    async def get_attribute_values(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID
    ) -> List[AttributeValueModel]:
        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found or belongs to another tenant.")
        return sorted(attribute.values, key=lambda x: x.value)

    @staticmethod
    async def create_attribute_value(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID,
        value: str,
        hex_code: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> AttributeValueModel:
        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found or belongs to another tenant.")
            
        value = value.strip()
        if not value:
            raise ValidationError("Attribute value cannot be empty.")
            
        if any(v.value.lower() == value.lower() for v in attribute.values):
            raise ValidationError(f"Value '{value}' already exists for this attribute.")
            
        new_val = AttributeValueModel(value=value, hex_code=hex_code)
        attribute.values.append(new_val)
        await attribute.save()
        return new_val

    @staticmethod
    async def delete_attribute_value(
        tenant_id: uuid.UUID,
        attribute_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found or belongs to another tenant.")
            
        initial_len = len(attribute.values)
        attribute.values = [v for v in attribute.values if v.id != attribute_value_id]
        
        if len(attribute.values) == initial_len:
            raise ValidationError("Attribute value not found.")
            
        await attribute.save()
        return True

    # --- Product Attribute Mapping ---

    @staticmethod
    async def assign_attribute_value_to_product(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        attribute_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        pricing_type_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> ProductAttributeModel:
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found.")

        attribute = await ProductService.get_attribute_by_id(tenant_id, attribute_id)
        if not attribute:
            raise ValidationError("Attribute not found.")
            
        attr_val = next((v for v in attribute.values if v.id == attribute_value_id), None)
        if not attr_val:
            raise ValidationError("Attribute value not found in attribute.")

        # Update or add
        existing = next((a for a in product.attributes if a.attribute_name == attribute.name and a.attribute_value == attr_val.value), None)
        if existing:
            existing.pricing_type_id = pricing_type_id
            existing.hex_code = attr_val.hex_code
            assigned = existing
        else:
            assigned = ProductAttributeModel(
                attribute_name=attribute.name,
                attribute_value=attr_val.value,
                hex_code=attr_val.hex_code,
                pricing_type_id=pricing_type_id
            )
            product.attributes.append(assigned)
            
        await product.save()
        return assigned

    @staticmethod
    async def remove_attribute_value_from_product(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        attribute_name: str,
        attribute_value: str,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found.")

        initial_len = len(product.attributes)
        product.attributes = [
            a for a in product.attributes 
            if not (a.attribute_name == attribute_name and a.attribute_value == attribute_value)
        ]
        
        if len(product.attributes) == initial_len:
            raise ValidationError("Attribute is not assigned to this product.")

        await product.save()
        return True

    # --- Product Group Management ---

    @staticmethod
    async def get_product_groups(tenant_id: uuid.UUID) -> List[ProductGroup]:
        return await ProductGroup.find({"tenant_id": tenant_id}).sort("name").to_list()

    @staticmethod
    async def get_product_group_by_id(
        tenant_id: uuid.UUID,
        group_id: uuid.UUID
    ) -> Optional[ProductGroup]:
        return await ProductGroup.find_one({"_id": group_id, "tenant_id": tenant_id})

    @staticmethod
    async def create_product_group(
        tenant_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> ProductGroup:
        name = name.strip()
        if not name:
            raise ValidationError("Product group name cannot be empty.")

        existing = await ProductGroup.find_one({"tenant_id": tenant_id, "name": name})
        if existing:
            raise ValidationError(f"Product group '{name}' already exists.")

        group = ProductGroup(
            tenant_id=tenant_id,
            name=name,
            description=description
        )
        await group.insert()
        return group

    @staticmethod
    async def delete_product_group(
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        group = await ProductService.get_product_group_by_id(tenant_id, group_id)
        if not group:
            raise ValidationError("Product group not found.")
        await group.delete()
        
        # Also remove this group from all products
        await Product.find({"tenant_id": tenant_id, "groups.group_id": group_id}).update(
            {"$pull": {"groups": {"group_id": group_id}}}
        )
        return True

    # --- Product Group Mapping ---

    @staticmethod
    async def link_product_to_group(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> ProductGroupLinkModel:
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found.")

        group = await ProductService.get_product_group_by_id(tenant_id, group_id)
        if not group:
            raise ValidationError("Product group not found.")

        if any(g.group_id == group_id for g in product.groups):
            return next(g for g in product.groups if g.group_id == group_id)

        link = ProductGroupLinkModel(group_id=group.id, group_name=group.name)
        product.groups.append(link)
        await product.save()
        return link

    @staticmethod
    async def unlink_product_from_group(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found.")

        initial_len = len(product.groups)
        product.groups = [g for g in product.groups if g.group_id != group_id]
        
        if len(product.groups) == initial_len:
            raise ValidationError("Product is not linked to this product group.")

        await product.save()
        return True

    @staticmethod
    async def get_related_products(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> List[Product]:
        """Fetch distinct related products sharing at least one group with product_id."""
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product or not product.groups:
            return []
            
        group_ids = [g.group_id for g in product.groups]
        
        return await Product.find({
            "tenant_id": tenant_id,
            "_id": {"$ne": product_id},
            "groups.group_id": {"$in": group_ids}
        }).to_list()

    # --- Product Stock Management ---

    @staticmethod
    async def get_product_stock(tenant_id: uuid.UUID, product_id: uuid.UUID) -> Optional[ProductStockModel]:
        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            return None
        return product.stock

    @staticmethod
    async def update_product_stock(
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        stock_value: int,
        user_id: Optional[uuid.UUID] = None
    ) -> ProductStockModel:
        if stock_value < 0:
            raise ValidationError("Stock value cannot be negative.")

        product = await ProductService.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found.")

        if not product.stock:
            product.stock = ProductStockModel(stock=stock_value)
        else:
            product.stock.stock = stock_value
            product.stock.updated_at = datetime.utcnow()

        await product.save()
        return product.stock

product_service = ProductService()
