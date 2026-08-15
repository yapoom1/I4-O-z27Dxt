# User API Documentation

This document describes the GraphQL queries, mutations, and authentication flows associated with user management in the Gubera E-Commerce platform.

---

## Headers Required for Requests

Most mutations require a **Tenant Context** or **Authentication Credentials**. These are supplied via HTTP Headers:

| Header | Description | Required For |
| :--- | :--- | :--- |
| `X-Tenant-ID` | UUID string representing the active Tenant. **(Optional if request hostname is mapped to a tenant)** | Almost all user operations and queries. |
| `Authorization` | Bearer token (`Bearer <access_token>`). | Authenticated queries/mutations (e.g., `me`, `createUser`). |

---

## Authentication Flows

### 1. Password Authentication Flow
For standard password-based login:
1. Provide the `X-Tenant-ID` header (or request from the tenant's mapped domain).
2. Call `loginWithPassword` mutation with either `email` or `mobilenumber` as `emailOrMobile` along with the plaintext `password`.
3. Receive access and refresh tokens.

#### Mutation Example
```graphql
mutation LoginWithPassword {
  loginWithPassword(
    emailOrMobile: "johndoe@example.com"
    password: "securepassword123"
  ) {
    tokens {
      accessToken
      refreshToken
      tokenType
    }
    user {
      id
      name
      email
      mobilenumber
      role
      status
    }
  }
}
```

---

### 2. SMS OTP Authentication Flow
For mobile-based OTP login:
1. Provide the `X-Tenant-ID` header (or request from the tenant's mapped domain).
2. Request an OTP using the `sendOtp` mutation. The server generates a 6-digit OTP, caches it in Redis (valid for 5 mins, throttled to 1 request per minute), and sends it via SMS gateway.
3. Submit the received OTP via the `loginWithOtp` mutation to receive access and refresh tokens.

> [!NOTE]
> If a user with this mobile number does not exist under the specified tenant, the system **automatically registers them** (creates an account with default role `USER` and name `"User <mobilenumber>"`) before completing the login and issuing tokens.

#### Step A: Request OTP
```graphql
mutation SendOtp {
  sendOtp(mobilenumber: "+15550199") {
    success
    message
    otp # Note: Provided in development mode output for ease of testing
  }
}
```

#### Step B: Verify OTP and Login
```graphql
mutation LoginWithOtp {
  loginWithOtp(
    mobilenumber: "+15550199"
    otp: "123456"
  ) {
    tokens {
      accessToken
      refreshToken
      tokenType
    }
    user {
      id
      name
      mobilenumber
      role
    }
  }
}
```

---

### 3. Refreshing the Token
Access tokens expire after a short duration (configured as 15 minutes by default). Use the `refreshToken` mutation to exchange a valid refresh token for a brand new set of tokens.

#### Mutation Example
```graphql
mutation RefreshToken {
  refreshToken(refreshToken: "<your_refresh_token_here>") {
    accessToken
    refreshToken
    tokenType
  }
}
```

---

## User Queries

### `me`
Retrieves information about the currently authenticated user based on the `Authorization` header.

#### Query
```graphql
query GetCurrentUser {
  me {
    id
    name
    email
    mobilenumber
    role
    status
    createdAt
  }
}
```

---

## User Mutations

### `createUser`
Creates a new user under the current tenant. 
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `name` (String, Required)
  - `mobilenumber` (String, Required)
  - `email` (String, Optional)
  - `password` (String, Optional)
  - `role` (UserRole Enum: `SUPER_ADMIN`,`TENANT_ADMIN`, `USER`)

#### Mutation
```graphql
mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    name
    email
    mobilenumber
    role
    status
  }
}
```
**Variables**:
```json
{
  "input": {
    "name": "Jane Smith",
    "mobilenumber": "+15550200",
    "email": "janesmith@example.com",
    "password": "anothersecurepassword",
    "role": "STORE_OWNER"
  }
}
```

---

### `updateUser`
Updates an existing user's details and associated media scoped to the active tenant.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `id` (UUID!, Required) - User record identifier.
  - `input` (`UpdateUserInput!`, Required) - Fields to update.

#### Mutation Example
```graphql
mutation UpdateUser($id: UUID!, $input: UpdateUserInput!) {
  updateUser(id: $id, input: $input) {
    id
    name
    email
    mobilenumber
    role
    status
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
  "id": "bd07f5ff-8a2b-471d-8fdd-e350d022f94d",
  "input": {
    "name": "Jane Smith Updated",
    "email": "janesmith_new@example.com",
    "media": [
      {
        "filePath": "/uploads/user_avatar_new.jpg",
        "mediaUrl": "https://example.com/uploads/user_avatar_new.jpg",
        "mediaType": "IMAGE",
        "fileExtension": "jpg",
        "altText": "Updated Profile Pic"
      }
    ]
  }
}
```

---

## User Address Queries

### `myAddresses`
Retrieves all addresses associated with the currently authenticated user.
- **Permissions**: Requires the caller to be authenticated.

#### Query
```graphql
query GetMyAddresses {
  myAddresses {
    id
    addressLine1
    addressLine2
    landmark
    pincode
    state
    district
    customerName
    phoneNumber
    isPrimary
    latLong
    thirdPartyAppAddress
  }
}
```

---

### `address(id)`
Retrieves a single address by ID for the currently authenticated user.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `id` (UUID!, Required)

#### Query
```graphql
query GetAddress($id: UUID!) {
  address(id: $id) {
    id
    addressLine1
    isPrimary
  }
}
```

---

## User Address Mutations

### `createUserAddress`
Creates a new address for the currently authenticated user. If `isPrimary` is set to `true`, all other addresses for the user are updated to `isPrimary = false`.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `addressLine1` (String!, Required)
  - `addressLine2` (String, Optional)
  - `landmark` (String, Optional)
  - `pincode` (String!, Required)
  - `state` (String!, Required)
  - `district` (String!, Required)
  - `customerName` (String!, Required)
  - `phoneNumber` (String!, Required)
  - `isPrimary` (Boolean, Optional, Default: `false`)
  - `latLong` (String, Optional)
  - `thirdPartyAppAddress` (String, Optional)

#### Mutation
```graphql
mutation CreateUserAddress($input: CreateUserAddressInput!) {
  createUserAddress(input: $input) {
    id
    addressLine1
    isPrimary
  }
}
```
**Variables**:
```json
{
  "input": {
    "addressLine1": "123 Main St",
    "addressLine2": "Suite 400",
    "landmark": "Near Clock Tower",
    "pincode": "123456",
    "state": "StateOne",
    "district": "DistrictOne",
    "customerName": "John Doe",
    "phoneNumber": "9988776655",
    "isPrimary": true,
    "latLong": "12.34,56.78",
    "thirdPartyAppAddress": "Google Maps Link or JSON"
  }
}
```

---

### `updateUserAddress`
Updates an existing address of the authenticated user. If `isPrimary` is updated to `true`, all other addresses for the user are set to `isPrimary = false`.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `id` (UUID!, Required)
  - `input` (`UpdateUserAddressInput!`, Required) - All fields in this input are optional.

#### Mutation
```graphql
mutation UpdateUserAddress($id: UUID!, $input: UpdateUserAddressInput!) {
  updateUserAddress(id: $id, input: $input) {
    id
    addressLine1
    isPrimary
  }
}
```
**Variables**:
```json
{
  "id": "fe6cde36-5da0-485f-bb3c-5371056bed68",
  "input": {
    "isPrimary": true
  }
}
```

---

### `deleteUserAddress`
Deletes an address belonging to the authenticated user.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `id` (UUID!, Required)

#### Mutation
```graphql
mutation DeleteUserAddress($id: UUID!) {
  deleteUserAddress(id: $id)
}
```

---

## Shopping Cart Queries

### `myCart`
Retrieves the active shopping cart details for the currently authenticated user. If the user doesn't have a cart yet, one is automatically generated.
- **Permissions**: Requires the caller to be authenticated.

#### Query
```graphql
query GetMyCart {
  myCart {
    id
    userId
    items {
      id
      productId
      quantity
      product {
        id
        title
      }
    }
  }
}
```

---

## Shopping Cart Mutations

### `addToCart`
Adds a product to the shopping cart. If the product is already in the cart, the quantity is incremented by the specified amount.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `quantity` (Int, Optional, Default: `1`)

#### Mutation
```graphql
mutation AddToCart($productId: UUID!, $quantity: Int!) {
  addToCart(productId: $productId, quantity: $quantity) {
    id
    items {
      id
      productId
      quantity
    }
  }
}
```

---

### `updateCartItem`
Updates the exact quantity of a product in the user's cart. If the quantity is set to `0` or negative, the product is removed from the cart.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `productId` (UUID!, Required)
  - `quantity` (Int!, Required)

#### Mutation
```graphql
mutation UpdateCartItem($productId: UUID!, $quantity: Int!) {
  updateCartItem(productId: $productId, quantity: $quantity) {
    id
    items {
      id
      productId
      quantity
    }
  }
}
```

---

### `removeFromCart`
Removes a specific product completely from the user's cart.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `productId` (UUID!, Required)

#### Mutation
```graphql
mutation RemoveFromCart($productId: UUID!) {
  removeFromCart(productId: $productId) {
    id
    items {
      id
      productId
    }
  }
}
```

---

### `clearCart`
Clears all items from the user's cart.
- **Permissions**: Requires the caller to be authenticated.

#### Mutation
```graphql
mutation ClearCart {
  clearCart {
    id
    items {
      id
    }
  }
}
```

---

## Types Reference

### `UserType`
Represents the User entity schema:
- `id` (UUID!): Unique user identifier.
- `name` (String!): Full name of the user.
- `email` (String): Email address.
- `mobilenumber` (String!): Mobile phone number.
- `role` (String!): System role (e.g. `TENANT_ADMIN`, `STORE_OWNER`).
- `status` (String!): Account status (`ACTIVE`, `INACTIVE`, etc.).
- `tenantId` (UUID): Associated Tenant identifier.
- `addresses` (`[UserAddressType!]!`): List of addresses belonging to the user.
- `cart` (`UserCartType`): The user's active shopping cart (Optional).

### `UserAddressType`
Represents a user address:
- `id` (UUID!): Unique address identifier.
- `userId` (UUID!): The associated user's ID.
- `addressLine1` (String!): Address line 1.
- `addressLine2` (String): Address line 2 (Optional).
- `landmark` (String): Nearby landmark (Optional).
- `pincode` (String!): PIN/Postal code.
- `state` (String!): State.
- `district` (String!): District.
- `customerName` (String!): Contact name for this address.
- `phoneNumber` (String!): Contact phone number.
- `isPrimary` (Boolean!): Flag indicating if this is the user's primary/default address.
- `latLong` (String): Latitude and longitude coordinates (Optional).
- `thirdPartyAppAddress` (String): Address information/identifier from third-party APIs like maps (Optional).
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.

### `UserCartType`
Represents a user's shopping cart:
- `id` (UUID!): Unique cart identifier.
- `userId` (UUID!): Owner user ID.
- `items` (`[CartItemType!]!`): List of items currently in the cart.
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.

### `CartItemType`
Represents a line item inside a shopping cart:
- `id` (UUID!): Unique cart item identifier.
- `cartId` (UUID!): Associated cart ID.
- `userId` (UUID!): Owner user ID.
- `productId` (UUID!): Associated product ID.
- `quantity` (Int!): Number of units in the cart.
- `product` (`ProductType!`): Resolved details of the product.
- `createdAt` (DateTime!): Creation timestamp.
- `updatedAt` (DateTime!): Last update timestamp.

### `CreateUserInput`
Used to create a new user:
- `name` (String!, Required)
- `mobilenumber` (String!, Required)
- `email` (String, Optional)
- `password` (String, Optional)
- `role` (UserRole Enum, Optional, Default: `USER`)
- `media` (`[CreateMediaInput!]`, Optional) - Nested media list to immediately create and link to the user.

### `UpdateUserInput`
Used to update an existing user (all fields are optional):
- `name` (String, Optional)
- `mobilenumber` (String, Optional)
- `email` (String, Optional)
- `password` (String, Optional)
- `role` (UserRole Enum, Optional)
- `status` (UserStatus Enum, Optional)
- `media` (`[CreateMediaInput!]`, Optional) - Nested media list. Providing this replaces all currently associated media for this user.

### `CreateUserAddressInput`
Used to create a new address.
- `addressLine1` (String!, Required)
- `addressLine2` (String, Optional)
- `landmark` (String, Optional)
- `pincode` (String!, Required)
- `state` (String!, Required)
- `district` (String!, Required)
- `customerName` (String!, Required)
- `phoneNumber` (String!, Required)
- `isPrimary` (Boolean, Optional, Default: `false`)
- `latLong` (String, Optional)
- `thirdPartyAppAddress` (String, Optional)

### `UpdateUserAddressInput`
Used to update an existing address (all fields are optional).
- `addressLine1` (String, Optional)
- `addressLine2` (String, Optional)
- `landmark` (String, Optional)
- `pincode` (String, Optional)
- `state` (String, Optional)
- `district` (String, Optional)
- `customerName` (String, Optional)
- `phoneNumber` (String, Optional)
- `isPrimary` (Boolean, Optional)
- `latLong` (String, Optional)
- `thirdPartyAppAddress` (String, Optional)

### `AuthPayload`
Returned on login operations:
- `tokens` (`AuthTokensType!`): The generated session tokens.
- `user` (`UserType!`): The authenticated user's details.

### `AuthTokensType`
- `accessToken` (String!): JWT access token.
- `refreshToken` (String!): JWT refresh token.
- `tokenType` (String!): Usually `"bearer"`.


## Loyalty Wallet & Referral APIs

### Wallet Queries & Mutations

#### `myWallet` Query
Retrieves the loyalty wallet points balance and recent transaction history for the logged-in customer.
- **Permissions**: Requires the caller to be authenticated.

```graphql
query {
  myWallet {
    id
    userId
    points
    createdAt
    updatedAt
    transactions {
      id
      points
      type
      remarks
      createdAt
    }
  }
}
```

#### `creditWallet` Mutation
Credits points to a user's loyalty wallet.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `userId` (UUID!, Required)
  - `points` (Float!, Required, positive)
  - `remarks` (String, Optional)

```graphql
mutation CreditWallet($userId: UUID!, $points: Float!, $remarks: String) {
  creditWallet(userId: $userId, points: $points, remarks: $remarks) {
    id
    points
    type
  }
}
```

#### `debitWallet` Mutation
Debits points from a user's loyalty wallet.
- **Permissions**: Requires the caller to be authenticated as `TENANT_ADMIN` or `SUPER_ADMIN`.
- **Inputs**:
  - `userId` (UUID!, Required)
  - `points` (Float!, Required, positive)
  - `remarks` (String, Optional)

```graphql
mutation DebitWallet($userId: UUID!, $points: Float!, $remarks: String) {
  debitWallet(userId: $userId, points: $points, remarks: $remarks) {
    id
    points
    type
  }
}
```

---

### Referral Queries & Mutations

#### `myReferral` Query
Retrieves the logged-in user's custom referral code configuration, total referral points earned, and referral claim histories.
- **Permissions**: Requires the caller to be authenticated.

```graphql
query {
  myReferral {
    id
    userId
    referralPoints
    referralCode
    createdAt
    updatedAt
    histories {
      id
      points
      referredEntity
      referredEntityId
      createdAt
    }
  }
}
```

#### `generateReferralCode` Mutation
Registers or retrieves the customer's custom referral code. If no `customCode` is specified, a unique referral code is auto-generated.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `customCode` (String, Optional) - Must be unique system-wide.

```graphql
mutation GenerateReferral($code: String) {
  generateReferralCode(customCode: $code) {
    referralCode
    referralPoints
  }
}
```

#### `claimReferral` Mutation
Submits a referral points claim using the referrer's unique referral code.
- **Permissions**: Requires the caller to be authenticated.
- **Inputs**:
  - `input` (ClaimReferralInput!, Required)
    - `referrerCode` (String!, Required) - Referrer's unique referral code.
    - `referredEntity` (String!, Required) - System entity category (`USER`, `PRODUCT`, `ORDER`).
    - `referredEntityId` (UUID, Optional) - ID of the referred user/product/order.
    - `points` (Float!, Required) - Referral points to award.
    - `paymentId` (UUID, Optional)
    - `orderId` (UUID, Optional)
    - `remarks` (String, Optional)

```graphql
mutation ClaimReferral($input: ClaimReferralInput!) {
  claimReferral(input: $input) {
    id
    points
    referredEntity
    referredEntityId
    createdAt
  }
}
```

