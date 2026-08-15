# Product API Documentation

This document describes the GraphQL queries, mutations, and types associated with product management in the Gubera E-Commerce platform.

---

## Headers Required for Requests

Most operations require a **Tenant Context** and administrative actions require **Authentication Credentials**. These are supplied via HTTP Headers:

| Header | Description | Required For |
| :--- | :--- | :--- |
| `X-Tenant-ID` | UUID string representing the active Tenant. **(Optional if request hostname is mapped to a tenant)** | All product operations and queries. |
| `Authorization` | Bearer token (`Bearer <access_token>`). | Authenticated mutations (e.g., `createProduct`, `updateProduct`, `deleteProduct`). |

---

## Product Queries

### `products`
Retrieves a list of all products scoped to the active tenant. Supports optional filtering by `productType` and text `search` (matching `title`, `subtitle`, or `sku`).
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `productType` (ProductTypeEnum, Optional)
  - `search` (String, Optional)

#### Query Example
```graphql
query GetProducts($productType: ProductTypeEnum, $search: String) {
  products(productType: $productType, search: $search) {
    id
    title
    subtitle
    sku
    productType
    parentId
  }
}
```
**Variables**:
```json
{
  "productType": "GOODS",
  "search": "Laptop"
}
```

---

### `product(id)`
Retrieves details of a single product by ID, including its parent product (if applicable) and child products (variants).
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `id` (UUID!, Required)

#### Query Example
```graphql
query GetProductDetails($id: UUID!) {
  product(id: $id) {
    id
    title
    sku
    productType
    parent {
      id
      title
    }
    children {
      id
      title
      sku
    }
  }
}
```
**Variables**:
```json
{
  "id": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2"
}
```

---

## Product Mutations

### `createProduct`
Creates a new product under the current tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `title` (String!, Required)
  - `productType` (ProductTypeEnum!, Required: `GOODS`, `SERVICE`, `OTHERS`)
  - `subtitle` (String, Optional)
  - `description` (String, Optional)
  - `descriptionLong` (String, Optional)
  - `sku` (String, Optional) - Must be unique per tenant if provided.
  - `parentId` (UUID, Optional) - Links product to a parent product (e.g. for variants).
  - `thumbnailMediaId` (UUID, Optional)

#### Mutation Example
```graphql
mutation CreateProduct($input: CreateProductInput!) {
  createProduct(input: $input) {
    id
    title
    sku
    productType
    parentId
  }
}
```
**Variables**:
```json
{
  "input": {
    "title": "Professional E-Commerce Laptop",
    "productType": "GOODS",
    "subtitle": "High-end developer laptop",
    "description": "Powerful laptop with 32GB RAM",
    "descriptionLong": "Detailed specifications including 1TB SSD, 32GB RAM, and 8-Core CPU.",
    "sku": "PROD-LAPTOP-123",
    "thumbnailMediaId": "11111111-1111-1111-1111-111111111111"
  }
}
```

---

### `updateProduct`
Updates fields on an existing product scoped to the active tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (UpdateProductInput!, Required) - All fields inside the input are optional.

#### Mutation Example
```graphql
mutation UpdateProduct($id: UUID!, $input: UpdateProductInput!) {
  updateProduct(id: $id, input: $input) {
    id
    title
    subtitle
    sku
  }
}
```
**Variables**:
```json
{
  "id": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2",
  "input": {
    "title": "Professional E-Commerce Laptop v2",
    "subtitle": "Updated laptop specifications"
  }
}
```

---

### `deleteProduct`
Deletes a product scoped to the active tenant. If the deleted product is a parent, all child products (variants) linked to it will also be deleted automatically via database cascade.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteProduct($id: UUID!) {
  deleteProduct(id: $id)
}
```
**Variables**:
```json
{
  "id": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2"
}
```

---

## Pricing Queries

### `pricingTypes`
Retrieves all pricing types (e.g. `selling_price`, `cost`) configured under the active tenant.
- **Permissions**: Public (scoped to the active Tenant).

#### Query Example
```graphql
query GetPricingTypes {
  pricingTypes {
    id
    type
  }
}
```

---

### `productPrices(productId)`
Retrieves all price values mapped to a specific product.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `productId` (UUID!, Required)

#### Query Example
```graphql
query GetProductPrices($productId: UUID!) {
  productPrices(productId: $productId) {
    id
    price
    pricingTypeId
    pricingType {
      type
    }
  }
}
```
**Variables**:
```json
{
  "productId": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2"
}
```

---

## Pricing Mutations

### `createPricingType`
Creates a new pricing category/classification under the tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `type` (String!, Required, case-insensitive unique)

#### Mutation Example
```graphql
mutation CreatePricingType($input: CreatePricingTypeInput!) {
  createPricingType(input: $input) {
    id
    type
  }
}
```
**Variables**:
```json
{
  "input": {
    "type": "selling_price"
  }
}
```

---

### `updatePricingType`
Updates the name/type string of an existing pricing category.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (UpdatePricingTypeInput!, Required)

#### Mutation Example
```graphql
mutation UpdatePricingType($id: UUID!, $input: UpdatePricingTypeInput!) {
  updatePricingType(id: $id, input: $input) {
    id
    type
  }
}
```
**Variables**:
```json
{
  "id": "e30e78ef-7a56-4bdf-87f5-a22d4157fae1",
  "input": {
    "type": "cost"
  }
}
```

---

### `deletePricingType`
Deletes a pricing category and cascades deletion to delete all associated product prices.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeletePricingType($id: UUID!) {
  deletePricingType(id: $id)
}
```
**Variables**:
```json
{
  "id": "e30e78ef-7a56-4bdf-87f5-a22d4157fae1"
}
```

---

### `setProductPrice`
Creates or updates a price value for a specific product and pricing type.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `pricingTypeId` (UUID!, Required)
  - `price` (Float!, Required, non-negative)

#### Mutation Example
```graphql
mutation SetProductPrice($input: SetProductPriceInput!) {
  setProductPrice(input: $input) {
    id
    price
    productId
    pricingTypeId
  }
}
```
**Variables**:
```json
{
  "input": {
    "productId": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2",
    "pricingTypeId": "e30e78ef-7a56-4bdf-87f5-a22d4157fae1",
    "price": 999.99
  }
}
```

---

### `deleteProductPrice`
Removes a mapped price value from a product.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `pricingTypeId` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteProductPrice($productId: UUID!, $pricingTypeId: UUID!) {
  deleteProductPrice(productId: $productId, pricingTypeId: $pricingTypeId)
}
```
**Variables**:
```json
{
  "productId": "56ff46aa-c19f-42a2-85b3-ba74b373ecf2",
  "pricingTypeId": "e30e78ef-7a56-4bdf-87f5-a22d4157fae1"
}
```

---

## Types Reference

### `ProductType`
Represents the Product entity schema:
- `id` (UUID!): Unique product identifier.
- `tenantId` (UUID!): The associated Tenant identifier.
- `parentId` (UUID): Associated parent product ID (for product variants).
- `title` (String!): Product title.
- `subtitle` (String): Product subtitle (Optional).
- `description` (String): Short description (Optional).
- `descriptionLong` (String): Long/Rich text description (Optional).
- `sku` (String): Stock Keeping Unit (Optional). Unique per tenant.
- `productType` (`ProductTypeEnum!`): System product classification (`GOODS`, `SERVICE`, `OTHERS`).
- `thumbnailMediaId` (UUID): Thumbnail media identifier (Optional).
- `price` (Float): **(Default Price Field)** Resolves directly to the value of the product's `selling_price` pricing type. Returns `null` if not set.
- `prices` (`[ProductPriceType!]!`): Resolved list of all mapped pricing configuration values for this product.
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.
- `parent` (`ProductType`): Field resolver returning the parent product details.
- `children` (`[ProductType!]!`): Field resolver returning all variants or sub-products.
- `attributes` (`[ProductAttributeValueType!]!`): Field resolver returning all attribute value mappings for this product (e.g. Color, Size).
- `groups` (`[ProductGroupLinkType!]!`): Field resolver returning all product group mappings for this product.
- `relatedProducts` (`[ProductType!]!`): Field resolver returning other products sharing at least one product group with this product.

### `PricingTypeType`
- `id` (UUID!): Pricing type category identifier.
- `tenantId` (UUID!): Mapped tenant context.
- `type` (String!): Category name (e.g. `selling_price`, `cost`, `dealer_price`).
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.

### `ProductPriceType`
- `id` (UUID!): Price identifier.
- `productId` (UUID!): Mapped product.
- `pricingTypeId` (UUID!): Associated pricing type.
- `price` (Float!): Assigned price.
- `pricingType` (`PricingTypeType!`): Field resolver returning the pricing category details.
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.

### `ProductTypeEnum`
- `GOODS`
- `SERVICE`
- `OTHERS`

### `CreateProductInput`
- `title` (String!, Required)
- `productType` (`ProductTypeEnum!`, Required)
- `subtitle` (String, Optional)
- `description` (String, Optional)
- `descriptionLong` (String, Optional)
- `sku` (String, Optional)
- `parentId` (UUID, Optional)
- `thumbnailMediaId` (UUID, Optional)

### `UpdateProductInput`
- `title` (String, Optional)
- `productType` (`ProductTypeEnum`, Optional)
- `subtitle` (String, Optional)
- `description` (String, Optional)
- `descriptionLong` (String, Optional)
- `sku` (String, Optional)
- `parentId` (UUID, Optional)
- `thumbnailMediaId` (UUID, Optional)

### `CreatePricingTypeInput`
- `type` (String!, Required)

### `UpdatePricingTypeInput`
- `type` (String!, Required)

### `SetProductPriceInput`
- `productId` (UUID!, Required)
- `pricingTypeId` (UUID!, Required)
- `price` (Float!, Required)

---

## Product Attribute Queries

### `attributes`
Retrieves a list of all configured attributes scoped to the active tenant.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**: None.

#### Query Example
```graphql
query GetAttributes {
  attributes {
    id
    name
    displayName
    values {
      id
      value
      hexCode
    }
  }
}
```

---

### `attribute(id)`
Retrieves details of a single attribute by ID.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `id` (UUID!, Required)

#### Query Example
```graphql
query GetAttributeDetails($id: UUID!) {
  attribute(id: $id) {
    id
    name
    displayName
    values {
      id
      value
    }
  }
}
```

---

### `attributeValues(attributeId)`
Retrieves all option values for a specific attribute.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `attributeId` (UUID!, Required)

#### Query Example
```graphql
query GetAttributeValues($attributeId: UUID!) {
  attributeValues(attributeId: $attributeId) {
    id
    value
    hexCode
    attribute {
      id
      name
    }
  }
}
```

---

## Product Attribute Mutations

### `createAttribute`
Creates a new attribute definition scoped to the active tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `name` (String!, Required) - URL/code-friendly name (e.g., `color`, `size`).
  - `displayName` (String!, Required) - User-friendly label (e.g., `Color`, `Size`).

#### Mutation Example
```graphql
mutation CreateAttribute($input: CreateAttributeInput!) {
  createAttribute(input: $input) {
    id
    name
    displayName
  }
}
```
**Variables**:
```json
{
  "input": {
    "name": "color",
    "displayName": "Color"
  }
}
```

---

### `updateAttribute`
Updates an existing attribute's definition.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (UpdateAttributeInput!, Required)

#### Mutation Example
```graphql
mutation UpdateAttribute($id: UUID!, $input: UpdateAttributeInput!) {
  updateAttribute(id: $id, input: $input) {
    id
    name
    displayName
  }
}
```

---

### `deleteAttribute`
Deletes an attribute definition, cascade-deleting all its values and product mappings.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteAttribute($id: UUID!) {
  deleteAttribute(id: $id)
}
```

---

### `createAttributeValue`
Creates a new option value under an attribute.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `attributeId` (UUID!, Required)
  - `value` (String!, Required) - e.g. `Red`, `XL`
  - `hexCode` (String, Optional) - Hex value for visual colors.

#### Mutation Example
```graphql
mutation CreateAttributeValue($input: CreateAttributeValueInput!) {
  createAttributeValue(input: $input) {
    id
    value
    hexCode
    attributeId
  }
}
```
**Variables**:
```json
{
  "input": {
    "attributeId": "3b6f007e-128a-4d2b-aa90-b1834279c13b",
    "value": "Red",
    "hexCode": "#FF0000"
  }
}
```

---

### `updateAttributeValue`
Updates an existing attribute value option.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (UpdateAttributeValueInput!, Required)

#### Mutation Example
```graphql
mutation UpdateAttributeValue($id: UUID!, $input: UpdateAttributeValueInput!) {
  updateAttributeValue(id: $id, input: $input) {
    id
    value
    hexCode
  }
}
```

---

### `deleteAttributeValue`
Deletes an attribute value option, cascade-deleting all product mappings.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteAttributeValue($id: UUID!) {
  deleteAttributeValue(id: $id)
}
```

---

### `assignAttributeValueToProduct`
Links an attribute value to a product (usually a child/variant product).
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `attributeValueId` (UUID!, Required)

#### Mutation Example
```graphql
mutation AssignAttributeValueToProduct($productId: UUID!, $attributeValueId: UUID!) {
  assignAttributeValueToProduct(productId: $productId, attributeValueId: $attributeValueId) {
    id
    productId
    attributeValueId
  }
}
```

---

### `removeAttributeValueFromProduct`
Removes an attribute value link from a product.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `attributeValueId` (UUID!, Required)

#### Mutation Example
```graphql
mutation RemoveAttributeValueFromProduct($productId: UUID!, $attributeValueId: UUID!) {
  removeAttributeValueFromProduct(productId: $productId, attributeValueId: $attributeValueId)
}
```

---

### `AttributeType`
Represents an Attribute definition:
- `id` (UUID!): Unique attribute identifier.
- `tenantId` (UUID!): The associated Tenant identifier.
- `name` (String!): Attribute code name (e.g. `color`, `size`).
- `displayName` (String!): User-facing display name (e.g. `Color`, `Size`).
- `createdAt` (DateTime!): Creation timestamp.
- `values` (`[AttributeValueType!]!`): Field resolver returning all selectable values configured for this attribute.

### `AttributeValueType`
Represents a selectable option value for an Attribute:
- `id` (UUID!): Unique option identifier.
- `attributeId` (UUID!): Parent Attribute identifier.
- `value` (String!): Value text (e.g. `Red`, `XL`).
- `hexCode` (String): Hexadecimal representation for colors (Optional).
- `createdAt` (DateTime!): Creation timestamp.
- `attribute` (`AttributeType!`): Field resolver returning the parent attribute details.

### `ProductAttributeValueType`
Represents a link mapping between a Product and an AttributeValue:
- `id` (UUID!): Mapping identifier.
- `productId` (UUID!): Associated Product identifier.
- `attributeValueId` (UUID!): Mapped AttributeValue identifier.
- `createdAt` (DateTime!): Mapping timestamp.
- `attributeValue` (`AttributeValueType!`): Field resolver returning the resolved attribute value details.

### `CreateAttributeInput`
- `name` (String!, Required)
- `displayName` (String!, Required)

### `UpdateAttributeInput`
- `name` (String!, Required)
- `displayName` (String!, Required)

### `CreateAttributeValueInput`
- `attributeId` (UUID!, Required)
- `value` (String!, Required)
- `hexCode` (String, Optional)

### `UpdateAttributeValueInput`
- `value` (String, Optional)
- `hexCode` (String, Optional)

---

## Product Grouping Queries

### `productGroups`
Retrieves a list of all product groups scoped to the active tenant.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**: None.

#### Query Example
```graphql
query GetProductGroups {
  productGroups {
    id
    name
    description
    products {
      id
      title
      sku
    }
  }
}
```

---

### `productGroup(id)`
Retrieves details of a single product group by ID.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `id` (UUID!, Required)

#### Query Example
```graphql
query GetProductGroupDetails($id: UUID!) {
  productGroup(id: $id) {
    id
    name
    description
    products {
      id
      title
    }
  }
}
```

---

## Product Grouping Mutations

### `createProductGroup`
Creates a new product group scoped to the active tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `name` (String!, Required) - Group name (e.g. `Trending`, `Winter Specials`).
  - `description` (String, Optional) - Brief description of the group.

#### Mutation Example
```graphql
mutation CreateProductGroup($input: CreateProductGroupInput!) {
  createProductGroup(input: $input) {
    id
    name
    description
  }
}
```
**Variables**:
```json
{
  "input": {
    "name": "Summer Electronics",
    "description": "Trending electronic gear for summer"
  }
}
```

---

### `updateProductGroup`
Updates an existing product group's details.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (UpdateProductGroupInput!, Required)

#### Mutation Example
```graphql
mutation UpdateProductGroup($id: UUID!, $input: UpdateProductGroupInput!) {
  updateProductGroup(id: $id, input: $input) {
    id
    name
    description
  }
}
```

---

### `deleteProductGroup`
Deletes a product group, cascade-deleting all its links.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteProductGroup($id: UUID!) {
  deleteProductGroup(id: $id)
}
```

---

### `linkProductToGroup`
Links a product to a product group.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `groupId` (UUID!, Required)

#### Mutation Example
```graphql
mutation LinkProductToGroup($productId: UUID!, $groupId: UUID!) {
  linkProductToGroup(productId: $productId, groupId: $groupId) {
    id
    productId
    groupId
  }
}
```

---

### `unlinkProductFromGroup`
Removes a product link from a product group.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `groupId` (UUID!, Required)

#### Mutation Example
```graphql
mutation UnlinkProductFromGroup($productId: UUID!, $groupId: UUID!) {
  unlinkProductFromGroup(productId: $productId, groupId: $groupId)
}
```

---

### `ProductGroupType`
Represents a Product Group:
- `id` (UUID!): Unique group identifier.
- `tenantId` (UUID!): The associated Tenant identifier.
- `name` (String!): Unique group name.
- `description` (String): Group description.
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.
- `products` (`[ProductType!]!`): Field resolver returning all products belonging to this group.

### `ProductGroupLinkType`
Represents a mapping link between a Product and a ProductGroup:
- `id` (UUID!): Link identifier.
- `productId` (UUID!): Associated Product identifier.
- `groupId` (UUID!): Associated ProductGroup identifier.
- `createdAt` (DateTime!): Mapping timestamp.
- `group` (`ProductGroupType!`): Field resolver returning the resolved product group details.

### `CreateProductGroupInput`
- `name` (String!, Required)
- `description` (String, Optional)

### `UpdateProductGroupInput`
- `name` (String, Optional)
- `description` (String, Optional)

---

## Category Queries

### `categories`
Retrieves a list of all categories scoped to the active tenant. Supports text `search` (matching category `title`, `subtitle`, or `sku`).
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `search` (String, Optional)

#### Query Example
```graphql
query GetCategories($search: String) {
  categories(search: $search) {
    id
    title
    sku
    parent {
      id
      title
    }
  }
}
```

---

### `category(id)`
Retrieves a single category by ID, including its parent and child categories.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `id` (UUID!, Required)

#### Query Example
```graphql
query GetCategoryDetails($id: UUID!) {
  category(id: $id) {
    id
    title
    sku
    parent {
      id
      title
    }
    children {
      id
      title
    }
    products {
      id
      title
    }
  }
}
```

---

## Category Mutations

### `createCategory`
Creates a new category under the current tenant.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `title` (String!, Required)
  - `parentId` (UUID, Optional)
  - `subtitle` (String, Optional)
  - `description` (String, Optional)
  - `descriptionLong` (String, Optional)
  - `sku` (String, Optional) - Must be unique per tenant.
  - `thumbnailMediaId` (UUID, Optional)
  - `media` (`[CreateMediaInput!]`, Optional) - Nested media list.

#### Mutation Example
```graphql
mutation CreateCategory($input: CreateCategoryInput!) {
  createCategory(input: $input) {
    id
    title
    media {
      id
      filePath
    }
  }
}
```

---

### `updateCategory`
Updates an existing category's fields and replaces its nested media list.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (`UpdateCategoryInput!`, Required)

#### Mutation Example
```graphql
mutation UpdateCategory($id: UUID!, $input: UpdateCategoryInput!) {
  updateCategory(id: $id, input: $input) {
    id
    title
    media {
      id
      filePath
    }
  }
}
```

---

### `deleteCategory`
Deletes a category from the database.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteCategory($id: UUID!) {
  deleteCategory(id: $id)
}
```

---

### `setProductCategories`
Sets/replaces all categories associated with a product (Many-to-Many).
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `productId` (UUID!, Required)
  - `categoryIds` (`[UUID!]!`, Required)

#### Mutation Example
```graphql
mutation SetProductCategories($productId: UUID!, $categoryIds: [UUID!]!) {
  setProductCategories(productId: $productId, categoryIds: $categoryIds) {
    id
    title
  }
}
```

---

## Category Types Reference

### `CategoryType`
- `id` (UUID!): Unique category identifier.
- `tenantId` (UUID!): Associated tenant ID.
- `parentId` (UUID): Optional parent category ID.
- `title` (String!): Category title.
- `subtitle` (String): Category subtitle.
- `description` (String): Short description.
- `descriptionLong` (String): Detailed description.
- `sku` (String): Unique category SKU code.
- `thumbnailMediaId` (UUID): Thumbnail media UUID.
- `parent` (`CategoryType`): Parent category.
- `children` (`[CategoryType!]!`): Sub-categories list.
- `products` (`[ProductType!]!`): Associated products.
- `thumbnail` (`MediaType`): Resolved thumbnail object.
- `media` (`[MediaType!]!`): Associated media attachments.

### `CreateCategoryInput`
- `title` (String!, Required)
- `parentId` (UUID, Optional)
- `subtitle` (String, Optional)
- `description` (String, Optional)
- `descriptionLong` (String, Optional)
- `sku` (String, Optional)
- `thumbnailMediaId` (UUID, Optional)
- `media` (`[CreateMediaInput!]`, Optional)

### `UpdateCategoryInput`
- `title` (String, Optional)
- `parentId` (UUID, Optional)
- `subtitle` (String, Optional)
- `description` (String, Optional)
- `descriptionLong` (String, Optional)
- `sku` (String, Optional)
- `thumbnailMediaId` (UUID, Optional)
- `media` (`[CreateMediaInput!]`, Optional)

---

## Coupon Queries

### `coupon`
Retrieves details of a coupon code by code name (tenant scoped).
- **Permissions**: Authenticated.
- **Inputs**:
  - `code` (String!, Required)

#### Query Example
```graphql
query GetCouponDetails($code: String!) {
  coupon(code: $code) {
    id
    code
    discountType
    discountValue
    minOrderValue
    maxDiscountAmount
    startDate
    endDate
    isActive
    rules
  }
}
```

---

### `coupons`
Retrieves all coupon codes created under the active tenant.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).

#### Query Example
```graphql
query GetAllCoupons {
  coupons {
    id
    code
    discountType
    discountValue
    isActive
  }
}
```

---

### `simulateCoupon`
Simulates applying a coupon code on the active user's shopping cart, returning the original total, discount applied, and the new total. Does not modify database tables.
- **Permissions**: Authenticated.
- **Inputs**:
  - `code` (String!, Required)

#### Query Example
```graphql
query SimulateCouponDiscount($code: String!) {
  simulateCoupon(code: $code) {
    isValid
    errorMessage
    discountApplied
    newTotal
    originalTotal
  }
}
```

---

## Coupon Mutations

### `createCoupon`
Creates a new promotional coupon code under the current tenant.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `code` (String!, Required)
  - `discountType` (String!, Required) - Must be `FLAT`, `PERCENTAGE`, or `FREE_SHIPPING`.
  - `discountValue` (Float!, Required) - Discount value amount.
  - `startDate` (DateTime!, Required)
  - `endDate` (DateTime!, Required)
  - `description` (String, Optional)
  - `minOrderValue` (Float, Optional, Default: `0.00`)
  - `maxDiscountAmount` (Float, Optional) - Cap for percentage discount.
  - `usageLimitTotal` (Int, Optional) - Max global redemptions allowed.
  - `usageLimitPerUser` (Int, Optional, Default: `1`) - Redemptions allowed per user.
  - `rules` (JSON, Optional) - Futuristic JSON object containing categories/products filters (e.g. `{"only_categories": ["uuid-cat-1"], "exclude_products": ["uuid-prod-1"]}`).

#### Mutation Example
```graphql
mutation CreateCoupon($input: CreateCouponInput!) {
  createCoupon(input: $input) {
    id
    code
    discountType
    rules
  }
}
```
**Variables**:
```json
{
  "input": {
    "code": "SUMMER20",
    "discountType": "PERCENTAGE",
    "discountValue": 20.00,
    "startDate": "2026-06-01T00:00:00Z",
    "endDate": "2026-06-30T23:59:59Z",
    "minOrderValue": 50.00,
    "maxDiscountAmount": 15.00,
    "rules": {
      "only_categories": ["9707cb6b-4e00-4ea1-b258-8547372d8a9e"]
    }
  }
}
```

---

### `updateCouponStatus`
Activates or deactivates a coupon code.
- **Permissions**: Requires administrative authentication (`TENANT_ADMIN` or `SUPER_ADMIN`).
- **Inputs**:
  - `id` (UUID!, Required)
  - `isActive` (Boolean!, Required)

#### Mutation Example
```graphql
mutation ToggleCoupon($id: UUID!, $isActive: Boolean!) {
  updateCouponStatus(id: $id, isActive: $isActive) {
    id
    code
    isActive
  }
}
```

---

### `applyCoupon`
Applies a coupon to checkout, creating a coupon usage log and incrementing total usage count.
- **Permissions**: Authenticated.
- **Inputs**:
  - `code` (String!, Required)
  - `orderId` (UUID!, Required) - Scoped order identifier.

#### Mutation Example
```graphql
mutation ApplyCouponToCheckout($code: String!, $orderId: UUID!) {
  applyCoupon(code: $code, orderId: $orderId) {
    isValid
    discountApplied
    newTotal
  }
}
```

---

## Coupon Types Reference

### `CouponType`
- `id` (UUID!): Unique coupon identifier.
- `tenantId` (UUID!): Associated tenant ID.
- `code` (String!): Normalized uppercase coupon code name.
- `description` (String): Coupon description.
- `discountType` (String!): `FLAT` or `PERCENTAGE` discount type.
- `discountValue` (Float!): Discount value.
- `minOrderValue` (Float!): Min cart subtotal required.
- `maxDiscountAmount` (Float): Percentage discount cap limit.
- `startDate` (DateTime!): Promo start datetime.
- `endDate` (DateTime!): Promo expiration datetime.
- `usageLimitTotal` (Int): Max overall redemptions.
- `usageLimitPerUser` (Int!): Max redemptions allowed per customer.
- `usageCount` (Int!): Number of times coupon has been redeemed.
- `isActive` (Boolean!): Enabled flag.
- `rules` (JSON!): Dynamic constraints/exclusions filters.

### `CartDiscountResult`
- `isValid` (Boolean!): True if cart meets eligibility requirements.
- `errorMessage` (String): Reason for coupon rejection.
- `discountApplied` (Float!): Computed discount price subtraction.
- `newTotal` (Float!): Cart total after discount application.
- `originalTotal` (Float!): Cart subtotal before discount.

### `CreateCouponInput`
- `code` (String!, Required)
- `discountType` (String!, Required)
- `discountValue` (Float!, Required)
- `startDate` (DateTime!, Required)
- `endDate` (DateTime!, Required)
- `description` (String, Optional)
- `minOrderValue` (Float, Optional, Default: `0.00`)
- `maxDiscountAmount` (Float, Optional)
- `usageLimitTotal` (Int, Optional)
- `usageLimitPerUser` (Int, Optional, Default: `1`)
- `rules` (JSON, Optional)


## Cart Coupon Mutations

### `applyCouponToCart`
Applies a coupon to the authenticated user's cart without incrementing the global usage count or creating a ledger.
```graphql
mutation ApplyCouponToCart($code: String!) {
  applyCouponToCart(code: $code) {
    id
    appliedCoupons {
      code
    }
    billSummary {
      itemTotal
      discountApplied
      grandTotal
    }
  }
}
```

### `removeCouponFromCart`
Removes a specific applied coupon code from the user's cart.
```graphql
mutation RemoveCouponFromCart($code: String!) {
  removeCouponFromCart(code: $code) {
    id
    appliedCoupons {
      code
    }
  }
}
```

### `clearCouponsFromCart`
Clears all applied coupon codes from the user's cart.
```graphql
mutation ClearCouponsFromCart {
  clearCouponsFromCart {
    id
    appliedCoupons {
      code
    }
  }
}
```


## Delivery APIs

### `deliveryQuotes` Query
Retrieves available shipping options (Standard/Express) with fee calculations and estimated days for the selected delivery address.
```graphql
query GetDeliveryQuotes($addressId: UUID!) {
  deliveryQuotes(addressId: $addressId) {
    serviceName
    deliveryFee
    estimatedDays
  }
}
```

### `selectDeliveryOption` Mutation
Associates a delivery address and selected service option with the user's shopping cart.
```graphql
mutation SelectDeliveryOption($addressId: UUID!, $serviceName: String!) {
  selectDeliveryOption(addressId: $addressId, serviceName: $serviceName) {
    id
    deliveryFee
    deliveryService
    estimatedDays
    deliveryAddressId
    billSummary {
      deliveryFee
      grandTotal
    }
  }
}
```


## Shopping Cart GraphQL Reference Updates

### `UserCartType`
- `appliedCoupons` ([CouponType!]!): List of coupons applied to the cart.
- `deliveryFee` (Float): Linked shipping service fee.
- `deliveryService` (String): Selected shipping service name (e.g. Standard/Express).
- `estimatedDays` (Int): Estimated transit days.
- `deliveryAddress` (UserAddressType): Link to the selected `UserAddress`.
- `billSummary` (BillSummaryType!): The nested checkout breakdown.

### `BillSummaryType`
- `itemTotal` (Float!): Sum of all cart item subtotal prices.
- `discountApplied` (Float!): Cumulative coupons discount applied.
- `deliveryFee` (Float!): Selected shipping service fee (defaulting to 0.00).
- `tax` (Float!): 5% mock tax calculated on the net total (itemTotal - discountApplied + deliveryFee).
- `grandTotal` (Float!): Final payable total (net total + tax).


## Orders, Split Payments & Returns APIs

### Mutations

#### `checkoutCart`
Converts active cart items, shipping selections, and coupons into an Order and nested OrderItems, clearing the cart.
```graphql
mutation CheckoutCart($paymentMethod: String!) {
  checkoutCart(paymentMethod: $paymentMethod) {
    id
    orderStatus
    paymentStatus
    grandTotal
    items {
      id
      productId
      quantity
      unitPrice
      subtotal
    }
  }
}
```

#### `recordPayment`
Records a payment attempt or partial payment for an order.
```graphql
mutation RecordPayment($orderId: UUID!, $amount: Float!, $paymentMethod: String!, $status: String!) {
  recordPayment(orderId: $orderId, amount: $amount, paymentMethod: $paymentMethod, status: $status) {
    id
    amount
    status
    paymentMethod
  }
}
```

#### `requestOrderReturn`
Submits a request to return specific quantities of order items.
```graphql
mutation RequestReturn($input: RequestReturnInput!) {
  requestOrderReturn(input: $input) {
    id
    status
    refundStatus
    items {
      orderItemId
      quantity
      condition
    }
  }
}
```

#### `approveOrderReturn`
Allows administrators to approve or reject a customer return request.
```graphql
mutation ApproveReturn($returnId: UUID!, $approved: Boolean!) {
  approveOrderReturn(returnId: $returnId, approved: $approved) {
    id
    status
    refundStatus
  }
}
```

#### `completeOrderReturn`
Sets return status to completed, issues a negative refund entry to the payment ledger, and updates order return status.
```graphql
mutation CompleteReturn($returnId: UUID!, $refundAmount: Float!) {
  completeOrderReturn(returnId: $returnId, refundAmount: $refundAmount) {
    id
    status
    refundStatus
    refundAmount
  }
}
```

### Queries

#### `myOrders`
Retrieves all orders placed by the currently logged-in customer.
```graphql
query GetMyOrders {
  myOrders {
    id
    orderStatus
    paymentStatus
    grandTotal
    createdAt
  }
}
```

#### `order`
Retrieves detailed fields of a specific order.
```graphql
query GetOrderDetails($id: UUID!) {
  order(id: $id) {
    id
    orderStatus
    paymentStatus
    grandTotal
    payments {
      amount
      paymentMethod
      status
    }
    returns {
      id
      status
      refundAmount
    }
  }
}
```

#### `tenantOrders`
Retrieves all order transactions scoped to the active tenant domain (Requires Admin permissions).
```graphql
query GetTenantOrders($status: String) {
  tenantOrders(status: $status) {
    id
    userId
    orderStatus
    paymentStatus
    grandTotal
  }
}

---

## Product Stock & Review APIs

### Stock Queries & Mutations

#### `updateProductStock` Mutation
Updates the physical inventory level for a specific product.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `stock` (Int!, Required, non-negative)

```graphql
mutation UpdateStock($productId: UUID!, $stock: Int!) {
  updateProductStock(productId: $productId, stock: $stock) {
    id
    productId
    tenantId
    stock
    createdAt
    updatedAt
  }
}
```

---

### Reviews & Ratings

#### `reviews` Query
Retrieves a list of all approved reviews for a given entity type (e.g. `PRODUCT`) and target ID.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `entityName` (String!, Required) - Must be `PRODUCT`.
  - `entityId` (UUID!, Required)

```graphql
query GetReviews($entityName: String!, $entityId: UUID!) {
  reviews(entityName: $entityName, entityId: $entityId) {
    id
    ratingPoints
    review
    status
    createdAt
  }
}
```

#### `adminReviews` Query
Retrieves all reviews configured in the tenant for moderation.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.

```graphql
query GetAdminReviews {
  adminReviews {
    id
    entityName
    entityId
    ratingPoints
    review
    status
    createdAt
  }
}
```

#### `createReview` Mutation
Creates a new user rating/review. Created reviews have status `PENDING` by default.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `input` (CreateReviewInput!, Required)
    - `entityName` (String!, Required) - Must be `PRODUCT`.
    - `entityId` (UUID!, Required)
    - `ratingPoints` (Int!, Required) - Integer between 1 and 5.
    - `review` (String, Optional) - Review content/comment.

```graphql
mutation CreateReview($input: CreateReviewInput!) {
  createReview(input: $input) {
    id
    entityName
    entityId
    ratingPoints
    review
    status
    createdAt
  }
}
```

#### `updateReviewStatus` Mutation
Updates a review status (approving or rejecting it).
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)
  - `status` (String!, Required) - Must be `APPROVED` or `REJECTED`.

```graphql
mutation ApproveOrRejectReview($id: UUID!, $status: String!) {
  updateReviewStatus(id: $id, status: $status) {
    id
    status
  }
}
```

```

