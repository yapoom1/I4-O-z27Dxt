import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import Document, Indexed

class ProductStockModel(BaseModel):
    """Embedded model representing stock levels."""
    stock: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductShippingModel(BaseModel):
    """Embedded model representing shipping dimensions."""
    weight: float        # kg (Mandatory)
    length: float = 10.0 # cm (Optional, default 10.0)
    width: float = 10.0  # cm (Optional, default 10.0)
    height: float = 10.0 # cm (Optional, default 10.0)

class ProductAttributeModel(BaseModel):
    """Embedded model representing an assigned attribute to a product."""
    attribute_name: str
    attribute_value: str
    hex_code: Optional[str] = None
    pricing_type_id: Optional[uuid.UUID] = None

class ProductGroupLinkModel(BaseModel):
    """Embedded model representing product group links."""
    group_id: uuid.UUID
    group_name: str

class AttributeValueModel(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    value: str
    hex_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Attribute(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    tenant_id: uuid.UUID
    name: str
    display_name: str
    values: List[AttributeValueModel] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "attributes"
        indexes = [[("tenant_id", 1), ("name", 1)]]

class ProductGroup(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "product_groups"
        indexes = [[("tenant_id", 1), ("name", 1)]]

class Product(Document):
    """Beanie document representing a Product in the multi-tenant system."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    tenant_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    
    # Relationships mapping previously stored in SQL join tables
    category_ids: List[uuid.UUID] = []
    
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    description_long: Optional[str] = None
    sku: Optional[str] = None
    product_type: str = "GOODS"
    thumbnail_media_id: Optional[uuid.UUID] = None
    
    # Embedded Data
    stock: Optional[ProductStockModel] = None
    shipping: Optional[ProductShippingModel] = None
    attributes: List[ProductAttributeModel] = []
    groups: List[ProductGroupLinkModel] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "products"
        indexes = [
            [("tenant_id", 1), ("sku", 1)],
            [("tenant_id", 1), ("category_ids", 1)]
        ]
