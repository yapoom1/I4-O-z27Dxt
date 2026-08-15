# Homepage Module Documentation

The Homepage Module provides a highly dynamic, multi-tenant API to manage and serve custom configurations for store homepages. It supports rendering banners, product carousels (both manual and dynamic), promotional sections, and category feeds.

## Core Concepts

- **HomepageConfig**: A single configuration document per tenant that holds the overall state (`status`, `version`) and an array of ordered `sections`.
- **HomepageSection**: An individual block on the homepage.
  - **Types**: `banner`, `products`, `categories`, `promo`.
  - **Config**: A dynamic JSON object defining the specifics for that section (e.g., product IDs, dynamic rules, or raw banner data).

---

## 1. Customer API (Public-Facing)

This endpoint is used by the frontend (React/Vue/Mobile) to render the homepage. It leverages **Redis Caching** for extreme performance and automatically aggregates product and category data.

### `GET /homepage`

Fetch the fully resolved and ordered homepage sections for a given tenant. Only returns configurations with `status: "published"`.

**Headers Required:**
- `X-Tenant-ID`: `<uuid>` (Or domain mapping)

**Response (200 OK):**
```json
{
  "tenant_id": "d34399b7-1102-40fe-aab8-8f67ebf22ddc",
  "version": 2,
  "status": "published",
  "updated_at": "2026-06-10T12:00:00.000Z",
  "sections": [
    {
      "id": "e93ab12c-5678-...",
      "type": "banner",
      "title": "Hero Section",
      "order": 1,
      "data": [
        {
          "title": "Summer Sale",
          "image_url": "https://example.com/banner.jpg",
          "order": 1
        }
      ]
    },
    {
      "id": "f82ab12c-1234-...",
      "type": "products",
      "title": "Best Sellers",
      "order": 2,
      "data": [
        {
          "id": "product-uuid-1",
          "title": "Cool T-Shirt",
          "subtitle": "Cotton",
          "sku": "TSHIRT-001",
          "thumbnail_media_id": "media-uuid"
        }
      ]
    }
  ]
}
```

---

## 2. Admin APIs

These endpoints manage the homepage configuration. They require the caller to be authenticated as an Admin (`SUPER_ADMIN` or `TENANT_ADMIN`). Changes to the configuration automatically invalidate the Redis cache.

**Headers Required for all Admin APIs:**
- `Authorization`: `Bearer <jwt_token>`
- `X-Tenant-ID`: `<uuid>`

### `GET /homepage/config`
Fetches the raw configuration document without resolving the product or category data. Used by the Admin Builder UI.

**Response (200 OK):**
```json
{
  "_id": "mongo-object-id",
  "tenant_id": "d34399b7-1102-40fe-aab8-8f67ebf22ddc",
  "version": 1,
  "status": "draft",
  "sections": [
    {
      "id": "e93ab12c-...",
      "type": "products",
      "title": "Best Sellers",
      "order": 1,
      "config": {
        "source_type": "dynamic",
        "source": "best_sellers",
        "limit": 10
      }
    }
  ],
  "created_at": "2026-06-10T12:00:00.000Z",
  "updated_at": "2026-06-10T12:00:00.000Z"
}
```

### `POST /homepage/config`
Creates or overwrites the entire homepage configuration for the tenant.

**Request Body:**
```json
{
  "status": "published", 
  "sections": [
    {
      "type": "banner",
      "title": "Main Hero",
      "order": 1,
      "config": {
        "banners": [
          {"title": "Promo 1", "image_url": "link", "order": 1}
        ]
      }
    },
    {
      "type": "products",
      "title": "New Arrivals",
      "order": 2,
      "config": {
        "source_type": "dynamic",
        "source": "new_arrivals",
        "limit": 8
      }
    }
  ]
}
```

### `PUT /homepage/config`
Updates specific top-level attributes (like changing the status from `draft` to `published` without sending the whole sections array).

**Request Body:**
```json
{
  "status": "published"
}
```

### `DELETE /homepage/section/{section_id}`
Removes a specific section from the homepage configuration by its UUID.

**Response (200 OK):**
```json
{
  "status": "deleted",
  "section_id": "e93ab12c-..."
}
```

---

## 3. Section Types and Configurations

When defining sections in the `POST` or `PUT` endpoints, the `config` object changes depending on the `type` of the section.

### A. Banner Section
`"type": "banner"`
```json
"config": {
  "banners": [
    {
      "title": "Sale",
      "image_url": "https://img.com/a.jpg",
      "link_url": "/category/sale",
      "order": 1
    }
  ]
}
```

### B. Product Section (Manual)
Allows admins to hand-pick specific products to display.
`"type": "products"`
```json
"config": {
  "source_type": "manual",
  "product_ids": [
    "uuid-1",
    "uuid-2"
  ]
}
```

### C. Product Section (Dynamic)
Automatically resolves products based on system data. Supported sources: `best_sellers`, `new_arrivals`, `category`.
`"type": "products"`
```json
"config": {
  "source_type": "dynamic",
  "source": "best_sellers", 
  "limit": 10
}
```
*Note: If `source` is `"category"`, you must provide `"category_id": "<uuid>"*

### D. Categories Section
Renders a list of category cards.
`"type": "categories"`
```json
"config": {
  "category_ids": [
    "cat-uuid-1",
    "cat-uuid-2"
  ]
}
```

### E. Promo Section
Raw HTML/Custom configurations for promotional text or banners.
`"type": "promo"`
```json
"config": {
  "html_content": "<div class='promo'>Free Shipping!</div>",
  "background_color": "#ff0000"
}
```
