# Media API Documentation

This document describes the GraphQL queries, mutations, types, and integration details associated with media management in the Gubera E-Commerce platform. The Media service provides a polymorphic media table allowing you to upload and link media files (images, videos, PDFs, etc.) to any system entity (such as products or users).

---

## Headers Required for Requests

Most operations require a **Tenant Context** and administrative actions require **Authentication Credentials**. These are supplied via HTTP Headers:

| Header | Description | Required For |
| :--- | :--- | :--- |
| `X-Tenant-ID` | UUID string representing the active Tenant. **(Optional if request hostname is mapped to a tenant)** | All media operations and queries. |
| `Authorization` | Bearer token (`Bearer <access_token>`). | Authenticated mutations (e.g., `createMedia`, `updateMedia`, `deleteMedia`). |

---

## GraphQL Types and Enums

### `MediaTypeEnum`
Enumeration of supported media types:
- `IMAGE`
- `VIDEO`
- `PDF`
- `AUDIO`
- `OTHER`

### `MediaType`
GraphQL representation of a Media record.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID!` | Unique identifier of the media record. |
| `tenantId` | `UUID!` | ID of the tenant owning the media. |
| `entityName` | `String` | Name of the entity this media is linked to (e.g., `"product"`, `"user"`). |
| `entityId` | `UUID` | UUID of the specific linked entity record. |
| `filePath` | `String!` | Local file path storage descriptor. |
| `mediaUrl` | `String!` | Public URL endpoint to retrieve/render the media file. |
| `mediaType` | `MediaTypeEnum!` | The type classification of the media. |
| `fileExtension` | `String` | File extension (e.g., `"png"`, `"jpg"`, `"mp4"`, `"pdf"`). |
| `altText` | `String` | Accessible alternative text descriptor. |
| `metaAttributes` | `JSON` | Flexible JSON storage containing metadata (e.g., `width`, `height`, `size` in bytes, `quality`, etc.). |
| `createdAt` | `DateTime!` | Creation timestamp. |
| `updatedAt` | `DateTime!` | Last update timestamp. |

---

## Media Queries

### `mediaList`
Fetches all media records scoped to the active tenant. Supports filtering by the linked entity details.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `entityName` (String, Optional) - Filter by linked entity classification.
  - `entityId` (UUID, Optional) - Filter by linked entity unique identifier.

#### Query Example
```graphql
query GetEntityMedia($entityName: String, $entityId: UUID) {
  mediaList(entityName: $entityName, entityId: $entityId) {
    id
    entityName
    entityId
    filePath
    mediaUrl
    mediaType
    fileExtension
    altText
    metaAttributes
  }
}
```
**Variables**:
```json
{
  "entityName": "product",
  "entityId": "5c9b151a-1f1f-4d1d-8820-f926e078bace"
}
```

---

### `media(id)`
Retrieves a single media record by its ID.
- **Permissions**: Public (scoped to the active Tenant).
- **Inputs**:
  - `id` (UUID!, Required)

#### Query Example
```graphql
query GetMediaDetails($id: UUID!) {
  media(id: $id) {
    id
    filePath
    mediaUrl
    mediaType
    altText
    metaAttributes
  }
}
```
**Variables**:
```json
{
  "id": "3fda9bc6-b3d0-4262-a827-e7c3dc58d2a8"
}
```

---

## Media Mutations

### `createMedia`
Registers a new media record under the active tenant.
- **Permissions**: Requires authentication as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `filePath` (String!, Required) - Storage path.
  - `mediaUrl` (String!, Required) - Public access URL.
  - `mediaType` (MediaTypeEnum, Optional: defaults to `IMAGE`)
  - `fileExtension` (String, Optional) - e.g., `"jpg"`, `"mp4"`.
  - `altText` (String, Optional) - Accessibility description.
  - `metaAttributes` (JSON, Optional) - Metadata JSON mapping.
  - `entityName` (String, Optional) - Target entity classification (e.g. `"product"`, `"user"`).
  - `entityId` (UUID, Optional) - Target entity ID.

#### Mutation Example
```graphql
mutation RegisterMedia($input: CreateMediaInput!) {
  createMedia(input: $input) {
    id
    filePath
    mediaUrl
    mediaType
    metaAttributes
    entityName
    entityId
  }
}
```
**Variables**:
```json
{
  "input": {
    "filePath": "/uploads/products/laptop.jpg",
    "mediaUrl": "https://cdn.example.com/uploads/products/laptop.jpg",
    "mediaType": "IMAGE",
    "fileExtension": "jpg",
    "altText": "Sleek developer laptop",
    "metaAttributes": {
      "width": 1024,
      "height": 768,
      "size": 150245
    },
    "entityName": "product",
    "entityId": "5c9b151a-1f1f-4d1d-8820-f926e078bace"
  }
}
```

---

### `updateMedia`
Updates fields on an existing media record.
- **Permissions**: Requires authentication as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required) - Target media record ID.
  - `input` (UpdateMediaInput!, Required) - Fields to update.

#### Mutation Example
```graphql
mutation UpdateMediaRecord($id: UUID!, $input: UpdateMediaInput!) {
  updateMedia(id: $id, input: $input) {
    id
    filePath
    mediaUrl
    altText
    metaAttributes
  }
}
```
**Variables**:
```json
{
  "id": "3fda9bc6-b3d0-4262-a827-e7c3dc58d2a8",
  "input": {
    "altText": "Updated alternative description",
    "metaAttributes": {
      "width": 2048,
      "height": 1536,
      "size": 420100
    }
  }
}
```

---

### `deleteMedia`
Deletes a media record from the database.
- **Permissions**: Requires authentication as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation Example
```graphql
mutation DeleteMediaRecord($id: UUID!) {
  deleteMedia(id: $id)
}
```
**Variables**:
```json
{
  "id": "3fda9bc6-b3d0-4262-a827-e7c3dc58d2a8"
}
```

---

## Polymorphic Schema Integrations

Media queries are integrated directly into the `Product` and `User` GraphQL types. Calling queries on these types will automatically resolve their linked media resources.

### 1. User Media
Resolves any media linked with `entityName = "user"` and matching `entityId = User.id`.

```graphql
query GetMyProfile {
  me {
    id
    name
    email
    media {
      id
      filePath
      mediaUrl
      mediaType
      altText
    }
  }
}
```

### 2. Product Media and Thumbnail
- `thumbnail`: Resolves a single `MediaType` linked via `Product.thumbnail_media_id`.
- `media`: Resolves all `[MediaType!]!` linked with `entityName = "product"` and matching `entityId = Product.id`.

```graphql
query GetProductWithImages($id: UUID!) {
  product(id: $id) {
    id
    title
    sku
    thumbnail {
      id
      mediaUrl
      altText
    }
    media {
      id
      mediaUrl
      mediaType
      altText
    }
  }
}
```

---

## Nested Creation and Editing with Media

You can create or update products and users along with their associated media list in a single GraphQL mutation call.

### 1. Create Product with Media
When creating a product, pass an array of media items in the `media` field under `CreateProductInput`.

#### Mutation Example
```graphql
mutation CreateProductWithMedia($input: CreateProductInput!) {
  createProduct(input: $input) {
    id
    title
    media {
      id
      filePath
      mediaUrl
    }
  }
}
```
**Variables**:
```json
{
  "input": {
    "title": "New Laptop Model",
    "productType": "GOODS",
    "sku": "LAPTOP-NESTED-123",
    "media": [
      {
        "filePath": "/uploads/nested_laptop_1.jpg",
        "mediaUrl": "https://example.com/uploads/nested_laptop_1.jpg",
        "mediaType": "IMAGE",
        "fileExtension": "jpg",
        "altText": "Front View",
        "metaAttributes": {"size": 45000}
      }
    ]
  }
}
```

### 2. Update Product with Media
When updating a product, providing a `media` list replaces all existing media entries for that product with the new ones.

#### Mutation Example
```graphql
mutation UpdateProductWithMedia($id: UUID!, $input: UpdateProductInput!) {
  updateProduct(id: $id, input: $input) {
    id
    title
    media {
      id
      filePath
    }
  }
}
```
**Variables**:
```json
{
  "id": "5c9b151a-1f1f-4d1d-8820-f926e078bace",
  "input": {
    "media": [
      {
        "filePath": "/uploads/nested_laptop_new1.jpg",
        "mediaUrl": "https://example.com/uploads/nested_laptop_new1.jpg",
        "mediaType": "IMAGE",
        "fileExtension": "jpg",
        "altText": "Updated View 1",
        "metaAttributes": {"size": 50000}
      }
    ]
  }
}
```

### 3. Create User with Media
When creating a user, pass an array of media items (e.g. verification documents, ID scans) in the `media` field under `CreateUserInput`.

#### Mutation Example
```graphql
mutation CreateUserWithMedia($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    name
    media {
      id
      filePath
    }
  }
}
```
**Variables**:
```json
{
  "input": {
    "name": "Alex Mercer",
    "mobilenumber": "9876543210",
    "email": "alex@example.com",
    "password": "Password123!",
    "media": [
      {
        "filePath": "/uploads/verification_doc.pdf",
        "mediaUrl": "https://example.com/uploads/verification_doc.pdf",
        "mediaType": "PDF",
        "fileExtension": "pdf",
        "altText": "ID Scan"
      }
    ]
  }
}
```

### 4. Update User with Media
Introduce profile updates and updated verification documents via `updateUser` mutation. Providing a `media` list replaces all existing user media entries.

#### Mutation Example
```graphql
mutation UpdateUserWithMedia($id: UUID!, $input: UpdateUserInput!) {
  updateUser(id: $id, input: $input) {
    id
    name
    media {
      id
      filePath
    }
  }
}
```
**Variables**:
```json
{
  "id": "bd07f5ff-8a2b-471d-8fdd-e350d022f94d",
  "input": {
    "name": "Alex Mercer Updated",
    "media": [
      {
        "filePath": "/uploads/new_verification_doc.pdf",
        "mediaUrl": "https://example.com/uploads/new_verification_doc.pdf",
        "mediaType": "PDF",
        "fileExtension": "pdf",
        "altText": "New ID Scan"
      }
    ]
  }
}
```
