# Tenant API Documentation

This document describes the GraphQL queries, mutations, and headers associated with multi-tenancy management in the Gubera E-Commerce platform.

---

## The Tenant Header Context

In a multi-tenant application, operations must be associated with a specific tenant namespace. This context is supplied using the `X-Tenant-ID` HTTP header:

```http
X-Tenant-ID: <Tenant_UUID>
```

- When querying active tenant information or performing authenticated mutations, the API parses the header to select database contexts.
- If the `X-Tenant-ID` header is omitted, the API will try to fall back to the `tenant_id` claim inside the decoded JWT token from the `Authorization` header.

---

## Host-Based Tenant Resolution (Domains)

If the `X-Tenant-ID` header is not provided and the requester is unauthenticated (or the authentication payload has no `tenant_id`), the API resolves the tenant dynamically using the **request hostname** (domain name):

1. The host domain (e.g. `clienta.example.com` or `localhost`) is retrieved from the incoming HTTP request.
2. The domain is checked against the `system_domains` table. If the domain is a registered system domain (e.g., the platform's core admin panel or main landing page), tenant resolution is **skipped** (meaning no tenant ID is populated for the request).
3. If it is not a system domain, the host is queried in the `tenant_domains` table to resolve the associated `tenant_id`.

### Related Tables:

#### `tenant_domains`
Maps custom/subdomains to tenants:
- `id` (UUID): Unique ID.
- `domain` (String): Normalized unique host domain name (e.g. `customer.com`).
- `tenant_id` (UUID): Reference to the associated tenant.
- `is_primary` (Boolean): Identifies the main custom domain for the tenant.

#### `system_domains`
Excludes specific hosts from custom tenant mapping resolution:
- `id` (UUID): Unique ID.
- `domain` (String): Normalized unique host domain name (e.g. `admin.gubera.com`).
- `description` (String): Optional context about the system site.

---

## Tenant Registration Flow

To register a new business (Tenant) on the platform, execute the `createTenant` mutation. Doing so:
1. Validates that the business name is unique.
2. Creates the Tenant record in the PostgreSQL database.
3. Hashes the administrator password and creates the tenant's initial `TENANT_ADMIN` user.
4. Logs a `TENANT_REGISTERED` audit event to the MongoDB audit collection.

---

## Tenant Mutations

### `createTenant`
Registers a new tenant business and creates the corresponding administrator user.

#### Mutation
```graphql
mutation RegisterTenant($input: CreateTenantInput!) {
  createTenant(input: $input) {
    id
    businessName
    createdAt
  }
}
```

**Variables**:
```json
{
  "input": {
    "businessName": "Acme Super Store",
    "adminName": "John Doe",
    "adminEmail": "johndoe@example.com",
    "adminMobile": "+15550199",
    "adminPassword": "securepassword123"
  }
}
```

---

## Tenant Queries

### `tenant`
Fetches the details of the active tenant from context or the authenticated user.

#### Query
```graphql
query GetActiveTenant {
  tenant {
    id
    businessName
    createdAt
  }
}
```

---

## Types Reference

### `TenantType`
Represents the Tenant entity schema:
- `id` (UUID!): Unique tenant identifier.
- `businessName` (String!): Name of the tenant's business.
- `createdAt` (String!): Date and time when the tenant was registered.

### `CreateTenantInput`
Input payload required for tenant registration:
- `businessName` (String!): Must be unique across the platform.
- `adminName` (String!): The name of the tenant's first admin user.
- `adminEmail` (String): The email address of the admin.
- `adminMobile` (String!): The mobile number of the admin (required for potential OTP logins).
- `adminPassword` (String): Plaintext password for password logins.
