# Frontend Integration Report: Next.js API Reference
frontend_reportThis document outlines all GraphQL Queries and Mutations available in the backend. It serves as a comprehensive reference for the Next.js frontend team.
frontend_report## General Guidelines
frontend_report- **Authentication**: For authenticated endpoints, include the header `Authorization: Bearer <token>`.
frontend_report- **Tenant Context**: Most endpoints require a tenant context. Include the header `X-Tenant-ID: <uuid>` or ensure the user is logged in to a tenant.

frontend_report## Module: `Auth`
frontend_report### Mutation: `AuthMutation`
frontend_report#### `send_otp`
frontend_report**Arguments:** `(mobilenumber: str)`  
frontend_report**Returns:** `SendOtpResult`  
frontend_report**Description:** Generate and dispatch an SMS OTP. Throttled to 1 request per minute.

frontend_report#### `login_with_otp`
frontend_report**Arguments:** `(mobilenumber: str, otp: str)`  
frontend_report**Returns:** `AuthPayload`  
frontend_report**Description:** Authenticate user using mobile number and SMS OTP code.

frontend_report#### `login_with_password`
frontend_report**Arguments:** `(email_or_mobile: str, password: str)`  
frontend_report**Returns:** `AuthPayload`  
frontend_report**Description:** Authenticate user using email/mobile and plaintext password.

frontend_report#### `refresh_token`
frontend_report**Arguments:** `(refresh_token: str)`  
frontend_report**Returns:** `AuthTokensType`  
frontend_report**Description:** Exchange a valid JWT refresh token for new access and refresh tokens.

frontend_report## Module: `Deliveries`
frontend_report### Query: `DeliveryQuery`
frontend_report#### `delivery_quotes`
frontend_report**Arguments:** `(address_id: uuid.UUID)`  
frontend_report**Returns:** `List[DeliveryOptionType]`  
frontend_report**Description:** Fetch available shipping quotes for the provided address.

frontend_report### Mutation: `DeliveryMutation`
frontend_report#### `select_delivery_option`
frontend_report**Arguments:** `(address_id: uuid.UUID, service_name: str)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Select a delivery quote and link it to the user's cart.

frontend_report## Module: `Homepage`
frontend_report### Query: `HomepageQuery`
frontend_report#### `published_homepage`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `strawberry.scalars.JSON`  
frontend_report**Description:** Fetch and resolve the published homepage configuration (Customer-facing).

frontend_report#### `homepage_config`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `HomepageConfigType`  
frontend_report**Description:** Fetch the raw homepage configuration (Admin API).

frontend_report### Mutation: `HomepageMutation`
frontend_report#### `create_or_update_homepage_config`
frontend_report**Arguments:** `(input: CreateOrUpdateHomepageConfigInput)`  
frontend_report**Returns:** `HomepageConfigType`  
frontend_report**Description:** Create or overwrite the tenant's homepage configuration (Admin API).

frontend_report#### `update_homepage_config`
frontend_report**Arguments:** `(input: UpdateHomepageConfigInput)`  
frontend_report**Returns:** `HomepageConfigType`  
frontend_report**Description:** Update specific attributes of the tenant's homepage configuration (Admin API).

frontend_report#### `delete_homepage_section`
frontend_report**Arguments:** `(section_id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a specific section from the homepage configuration (Admin API).

frontend_report## Module: `Media`
frontend_report### Query: `MediaQuery`
frontend_report#### `media_list`
frontend_report**Arguments:** `(entity_name: Optional[str], entity_id: Optional[uuid.UUID])`  
frontend_report**Returns:** `List[MediaType]`  
frontend_report**Description:** Fetch media records scoped to the current tenant.

frontend_report#### `media`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[MediaType]`  
frontend_report**Description:** Fetch a single media record by ID scoped to the current tenant.

frontend_report### Mutation: `MediaMutation`
frontend_report#### `create_media`
frontend_report**Arguments:** `(input: CreateMediaInput)`  
frontend_report**Returns:** `MediaType`  
frontend_report**Description:** Register a new media record (Requires Admin permissions).

frontend_report#### `update_media`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateMediaInput)`  
frontend_report**Returns:** `MediaType`  
frontend_report**Description:** Update fields on an existing media record (Requires Admin permissions).

frontend_report#### `delete_media`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a media record scoped to the current tenant (Requires Admin permissions).

frontend_report## Module: `Orders`
frontend_report### Query: `OrderQuery`
frontend_report#### `my_orders`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[OrderType]`  
frontend_report**Description:** Fetch all orders placed by the currently authenticated customer.

frontend_report#### `order`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[OrderType]`  
frontend_report**Description:** Fetch details of a single order by ID.

frontend_report#### `tenant_orders`
frontend_report**Arguments:** `(status: Optional[str])`  
frontend_report**Returns:** `List[OrderType]`  
frontend_report**Description:** Fetch all orders under the current tenant (Requires Admin permissions).

frontend_report### Mutation: `OrderMutation`
frontend_report#### `checkout_cart`
frontend_report**Arguments:** `(payment_method: str)`  
frontend_report**Returns:** `OrderType`  
frontend_report**Description:** Process checkout: convert shopping cart to Order, log coupon redemptions, and clear the cart.

frontend_report#### `record_payment`
frontend_report**Arguments:** `(order_id: uuid.UUID, amount: float, payment_method: str, transaction_reference: Optional[str], status: str)`  
frontend_report**Returns:** `OrderPaymentType`  
frontend_report**Description:** Record a payment transaction for an order.

frontend_report#### `request_order_return`
frontend_report**Arguments:** `(input: RequestReturnInput)`  
frontend_report**Returns:** `OrderReturnType`  
frontend_report**Description:** Submit an order return request for review.

frontend_report#### `approve_order_return`
frontend_report**Arguments:** `(return_id: uuid.UUID, approved: bool)`  
frontend_report**Returns:** `OrderReturnType`  
frontend_report**Description:** Approve or reject a return request (Requires Admin permissions).

frontend_report#### `complete_order_return`
frontend_report**Arguments:** `(return_id: uuid.UUID, refund_amount: float)`  
frontend_report**Returns:** `OrderReturnType`  
frontend_report**Description:** Mark return request as resolved and issue a refund balance (Requires Admin permissions).

frontend_report## Module: `Payments`
frontend_report### Query: `PaymentQuery`
frontend_report#### `platform_gateways`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[PaymentGatewayType]`  
frontend_report**Description:** List all platform-level payment gateways (Requires SUPER_ADMIN).

frontend_report#### `active_platform_gateway`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `Optional[PaymentGatewayType]`  
frontend_report**Description:** Fetch the currently active platform-level gateway.

frontend_report#### `tenant_gateways`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[TenantPaymentGatewayType]`  
frontend_report**Description:** List all configured payment gateways for the current tenant (Requires Admin permissions).

frontend_report#### `tenant_commission`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `Optional[TenantCommissionType]`  
frontend_report**Description:** Fetch the commission routing configuration for the current tenant (Requires Admin permissions).

frontend_report### Mutation: `PaymentMutation`
frontend_report#### `configure_platform_gateway`
frontend_report**Arguments:** `(input: ConfigurePlatformGatewayInput)`  
frontend_report**Returns:** `PaymentGatewayType`  
frontend_report**Description:** Configure or update a platform gateway profile (Requires SUPER_ADMIN).

frontend_report#### `activate_platform_gateway`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `PaymentGatewayType`  
frontend_report**Description:** Activate a platform gateway and deactivate others (Requires SUPER_ADMIN).

frontend_report#### `configure_tenant_gateway`
frontend_report**Arguments:** `(input: ConfigureTenantGatewayInput)`  
frontend_report**Returns:** `TenantPaymentGatewayType`  
frontend_report**Description:** Configure a tenant-specific gateway credential (Requires Admin permissions).

frontend_report#### `activate_tenant_gateway`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `TenantPaymentGatewayType`  
frontend_report**Description:** Activate a tenant gateway and deactivate others (Requires Admin permissions).

frontend_report#### `configure_tenant_commission`
frontend_report**Arguments:** `(input: ConfigureTenantCommissionInput)`  
frontend_report**Returns:** `TenantCommissionType`  
frontend_report**Description:** Configure the commission percentage & linked routing account for platform fallback route (Requires Admin permissions).

frontend_report#### `initiate_online_payment`
frontend_report**Arguments:** `(order_id: uuid.UUID)`  
frontend_report**Returns:** `InitiatePaymentResult`  
frontend_report**Description:** Initiate payment for an order, creating a pending payment transaction (Requires Authenticated User).

frontend_report#### `initiate_cart_payment`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `InitiatePaymentResult`  
frontend_report**Description:** Initiate payment for the current user's cart (Requires Authenticated User).

frontend_report## Module: `Categories`
frontend_report### Query: `CategoryQuery`
frontend_report#### `categories`
frontend_report**Arguments:** `(search: Optional[str])`  
frontend_report**Returns:** `List[CategoryType]`  
frontend_report**Description:** Fetch categories scoped to the current tenant.

frontend_report#### `category`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[CategoryType]`  
frontend_report**Description:** Fetch a single category by ID scoped to the current tenant.

frontend_report### Mutation: `CategoryMutation`
frontend_report#### `create_category`
frontend_report**Arguments:** `(input: CreateCategoryInput)`  
frontend_report**Returns:** `CategoryType`  
frontend_report**Description:** Create a new category (Requires Admin permissions).

frontend_report#### `update_category`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateCategoryInput)`  
frontend_report**Returns:** `CategoryType`  
frontend_report**Description:** Update an existing category scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_category`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a category scoped to the current tenant (Requires Admin permissions).

frontend_report#### `set_product_categories`
frontend_report**Arguments:** `(product_id: uuid.UUID, category_ids: List[uuid.UUID])`  
frontend_report**Returns:** `List[CategoryType]`  
frontend_report**Description:** Replace all categories associated with a product (Requires Admin permissions).

frontend_report## Module: `Pricing`
frontend_report### Query: `PricingQuery`
frontend_report#### `pricing_types`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[PricingTypeType]`  
frontend_report**Description:** Fetch all pricing types configured under the current tenant.

frontend_report#### `product_prices`
frontend_report**Arguments:** `(product_id: uuid.UUID)`  
frontend_report**Returns:** `List[ProductPriceType]`  
frontend_report**Description:** Fetch all price mappings for a specific product scoped to the current tenant.

frontend_report#### `product_pricing_rules`
frontend_report**Arguments:** `(product_id: uuid.UUID)`  
frontend_report**Returns:** `List[ProductPricingRuleType]`  
frontend_report**Description:** Fetch all pricing rules for a product (Requires Admin permissions).

frontend_report### Mutation: `PricingMutation`
frontend_report#### `create_pricing_type`
frontend_report**Arguments:** `(input: CreatePricingTypeInput)`  
frontend_report**Returns:** `PricingTypeType`  
frontend_report**Description:** Create a new pricing type scoped to the current tenant (Requires Admin permissions).

frontend_report#### `update_pricing_type`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdatePricingTypeInput)`  
frontend_report**Returns:** `PricingTypeType`  
frontend_report**Description:** Update an existing pricing type scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_pricing_type`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a pricing type scoped to the current tenant (Requires Admin permissions).

frontend_report#### `set_product_price`
frontend_report**Arguments:** `(input: SetProductPriceInput)`  
frontend_report**Returns:** `ProductPriceType`  
frontend_report**Description:** Set or update a specific price mapping for a product (Requires Admin permissions).

frontend_report#### `delete_product_price`
frontend_report**Arguments:** `(product_id: uuid.UUID, pricing_type_id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a product price mapping (Requires Admin permissions).

frontend_report#### `create_product_pricing_rule`
frontend_report**Arguments:** `(input: CreateProductPricingRuleInput)`  
frontend_report**Returns:** `ProductPricingRuleType`  
frontend_report**Description:** Create a dynamic pricing rule (Requires Admin permissions).

frontend_report#### `delete_product_pricing_rule`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a dynamic pricing rule (Requires Admin permissions).

frontend_report## Module: `Products`
frontend_report### Query: `ProductQuery`
frontend_report#### `products`
frontend_report**Arguments:** `(product_type: Optional[ProductTypeEnum], search: Optional[str])`  
frontend_report**Returns:** `List[ProductType]`  
frontend_report**Description:** Fetch products scoped to the current tenant.

frontend_report#### `product`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[ProductType]`  
frontend_report**Description:** Fetch a single product by ID scoped to the current tenant.

frontend_report#### `attributes`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[AttributeType]`  
frontend_report**Description:** Fetch all attributes configured under the current tenant.

frontend_report#### `attribute`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[AttributeType]`  
frontend_report**Description:** Fetch a single attribute by ID scoped to the current tenant.

frontend_report#### `attribute_values`
frontend_report**Arguments:** `(attribute_id: uuid.UUID)`  
frontend_report**Returns:** `List[AttributeValueType]`  
frontend_report**Description:** Fetch all option values for a specific attribute scoped to the current tenant.

frontend_report#### `product_groups`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[ProductGroupType]`  
frontend_report**Description:** Fetch all product groups scoped to the current tenant.

frontend_report#### `product_group`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[ProductGroupType]`  
frontend_report**Description:** Fetch a single product group by ID scoped to the current tenant.

frontend_report### Mutation: `ProductMutation`
frontend_report#### `create_product`
frontend_report**Arguments:** `(input: CreateProductInput)`  
frontend_report**Returns:** `ProductType`  
frontend_report**Description:** Create a new product under the current tenant (Requires Admin permissions).

frontend_report#### `update_product`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateProductInput)`  
frontend_report**Returns:** `ProductType`  
frontend_report**Description:** Update an existing product scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_product`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a product scoped to the current tenant (Requires Admin permissions).

frontend_report#### `create_attribute`
frontend_report**Arguments:** `(input: CreateAttributeInput)`  
frontend_report**Returns:** `AttributeType`  
frontend_report**Description:** Create a new attribute under the current tenant (Requires Admin permissions).

frontend_report#### `update_attribute`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateAttributeInput)`  
frontend_report**Returns:** `AttributeType`  
frontend_report**Description:** Update an existing attribute scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_attribute`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete an attribute scoped to the current tenant (Requires Admin permissions).

frontend_report#### `create_attribute_value`
frontend_report**Arguments:** `(input: CreateAttributeValueInput)`  
frontend_report**Returns:** `AttributeValueType`  
frontend_report**Description:** Create a new attribute value scoped to the current tenant (Requires Admin permissions).

frontend_report#### `update_attribute_value`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateAttributeValueInput)`  
frontend_report**Returns:** `AttributeValueType`  
frontend_report**Description:** Update an existing attribute value scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_attribute_value`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete an attribute value scoped to the current tenant (Requires Admin permissions).

frontend_report#### `assign_attribute_value_to_product`
frontend_report**Arguments:** `(product_id: uuid.UUID, attribute_value_id: uuid.UUID, pricing_type_id: Optional[uuid.UUID])`  
frontend_report**Returns:** `ProductAttributeValueType`  
frontend_report**Description:** Link an attribute value option to a product (Requires Admin permissions).

frontend_report#### `remove_attribute_value_from_product`
frontend_report**Arguments:** `(product_id: uuid.UUID, attribute_value_id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Remove an attribute value link from a product (Requires Admin permissions).

frontend_report#### `create_product_group`
frontend_report**Arguments:** `(input: CreateProductGroupInput)`  
frontend_report**Returns:** `ProductGroupType`  
frontend_report**Description:** Create a new product group scoped to the current tenant (Requires Admin permissions).

frontend_report#### `update_product_group`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateProductGroupInput)`  
frontend_report**Returns:** `ProductGroupType`  
frontend_report**Description:** Update an existing product group scoped to the current tenant (Requires Admin permissions).

frontend_report#### `delete_product_group`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete a product group scoped to the current tenant (Requires Admin permissions).

frontend_report#### `link_product_to_group`
frontend_report**Arguments:** `(product_id: uuid.UUID, group_id: uuid.UUID)`  
frontend_report**Returns:** `ProductGroupLinkType`  
frontend_report**Description:** Link a product to a product group (Requires Admin permissions).

frontend_report#### `unlink_product_from_group`
frontend_report**Arguments:** `(product_id: uuid.UUID, group_id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Unlink a product from a product group (Requires Admin permissions).

frontend_report#### `update_product_stock`
frontend_report**Arguments:** `(product_id: uuid.UUID, stock: int)`  
frontend_report**Returns:** `ProductStockType`  
frontend_report**Description:** Create or update product stock level (Requires Admin permissions).

frontend_report## Module: `Promotions`
frontend_report### Query: `CouponQuery`
frontend_report#### `coupon`
frontend_report**Arguments:** `(code: str)`  
frontend_report**Returns:** `Optional[CouponType]`  
frontend_report**Description:** Fetch details of a coupon code by code.

frontend_report#### `coupons`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[CouponType]`  
frontend_report**Description:** Fetch all promotional coupons (Requires Admin permissions).

frontend_report#### `simulate_coupon`
frontend_report**Arguments:** `(code: str)`  
frontend_report**Returns:** `CartDiscountResult`  
frontend_report**Description:** Simulate applying a coupon code on the active user's shopping cart.

frontend_report### Mutation: `CouponMutation`
frontend_report#### `create_coupon`
frontend_report**Arguments:** `(input: CreateCouponInput)`  
frontend_report**Returns:** `CouponType`  
frontend_report**Description:** Create a new promotional coupon code (Requires Admin permissions).

frontend_report#### `update_coupon_status`
frontend_report**Arguments:** `(id: uuid.UUID, is_active: bool)`  
frontend_report**Returns:** `CouponType`  
frontend_report**Description:** Activate or deactivate a coupon code (Requires Admin permissions).

frontend_report#### `apply_coupon`
frontend_report**Arguments:** `(code: str, order_id: uuid.UUID)`  
frontend_report**Returns:** `CartDiscountResult`  
frontend_report**Description:** Apply a coupon code, write a ledger entry, and increment the coupon usage counter.

frontend_report## Module: `Referral`
frontend_report### Query: `ReferralQuery`
frontend_report#### `my_referral`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `Optional[UserReferralType]`  
frontend_report**Description:** Fetch referral info of the currently authenticated user.

frontend_report### Mutation: `ReferralMutation`
frontend_report#### `generate_referral_code`
frontend_report**Arguments:** `(custom_code: Optional[str])`  
frontend_report**Returns:** `UserReferralType`  
frontend_report**Description:** Register or retrieve custom referral code configuration for the authenticated user.

frontend_report#### `claim_referral`
frontend_report**Arguments:** `(input: ClaimReferralInput)`  
frontend_report**Returns:** `UserReferralHistoryType`  
frontend_report**Description:** Claim referral points for the authenticated user using referrer's code.

frontend_report## Module: `Reviews`
frontend_report### Query: `ReviewQuery`
frontend_report#### `product_reviews`
frontend_report**Arguments:** `(product_id: uuid.UUID)`  
frontend_report**Returns:** `List[ProductReviewType]`  
frontend_report**Description:** Fetch all approved reviews for a product.

frontend_report#### `order_reviews`
frontend_report**Arguments:** `(order_id: uuid.UUID)`  
frontend_report**Returns:** `List[OrderReviewType]`  
frontend_report**Description:** Fetch all approved reviews for an order.

frontend_report#### `company_reviews`
frontend_report**Arguments:** `(tenant_id: uuid.UUID)`  
frontend_report**Returns:** `List[CompanyReviewType]`  
frontend_report**Description:** Fetch all approved reviews for a company/tenant.

frontend_report#### `admin_product_reviews`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[ProductReviewType]`  
frontend_report**Description:** Fetch all product reviews for administration/moderation (Requires Admin permissions).

frontend_report#### `admin_order_reviews`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[OrderReviewType]`  
frontend_report**Description:** Fetch all order reviews for administration/moderation (Requires Admin permissions).

frontend_report#### `admin_company_reviews`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `List[CompanyReviewType]`  
frontend_report**Description:** Fetch all company reviews for administration/moderation (Requires Admin permissions).

frontend_report### Mutation: `ReviewMutation`
frontend_report#### `create_product_review`
frontend_report**Arguments:** `(input: CreateProductReviewInput)`  
frontend_report**Returns:** `ProductReviewType`  
frontend_report**Description:** Create a new pending review for a product.

frontend_report#### `create_order_review`
frontend_report**Arguments:** `(input: CreateOrderReviewInput)`  
frontend_report**Returns:** `OrderReviewType`  
frontend_report**Description:** Create a new pending review for an order.

frontend_report#### `create_company_review`
frontend_report**Arguments:** `(input: CreateCompanyReviewInput)`  
frontend_report**Returns:** `CompanyReviewType`  
frontend_report**Description:** Create a new pending review for a company/tenant.

frontend_report#### `update_product_review_status`
frontend_report**Arguments:** `(id: uuid.UUID, status: str)`  
frontend_report**Returns:** `ProductReviewType`  
frontend_report**Description:** Approve or reject a product review (Requires Admin permissions).

frontend_report#### `update_order_review_status`
frontend_report**Arguments:** `(id: uuid.UUID, status: str)`  
frontend_report**Returns:** `OrderReviewType`  
frontend_report**Description:** Approve or reject an order review (Requires Admin permissions).

frontend_report#### `update_company_review_status`
frontend_report**Arguments:** `(id: uuid.UUID, status: str)`  
frontend_report**Returns:** `CompanyReviewType`  
frontend_report**Description:** Approve or reject a company review (Requires Admin permissions).

frontend_report## Module: `Tenants`
frontend_report### Query: `TenantQuery`
frontend_report#### `tenant`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `Optional[TenantType]`  
frontend_report**Description:** Fetch details of the active tenant from context or authenticated user.

frontend_report### Mutation: `TenantMutation`
frontend_report#### `create_tenant`
frontend_report**Arguments:** `(input: CreateTenantInput)`  
frontend_report**Returns:** `TenantType`  
frontend_report**Description:** Register a new Tenant alongside its Administrator user.

frontend_report## Module: `Users`
frontend_report### Query: `UserQuery`
frontend_report#### `me`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `UserType`  
frontend_report**Description:** Fetch details of the currently authenticated user.

frontend_report#### `my_addresses`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `list[UserAddressType]`  
frontend_report**Description:** Fetch all addresses of the currently authenticated user.

frontend_report#### `address`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `Optional[UserAddressType]`  
frontend_report**Description:** Fetch a single address of the currently authenticated user by ID.

frontend_report#### `my_cart`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Fetch details of the currently authenticated user's cart (creates one if none exists).

frontend_report### Mutation: `UserMutation`
frontend_report#### `create_user`
frontend_report**Arguments:** `(input: CreateUserInput)`  
frontend_report**Returns:** `UserType`  
frontend_report**Description:** Create a user inside the current active tenant (Requires Admin permissions).

frontend_report#### `update_user`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateUserInput)`  
frontend_report**Returns:** `UserType`  
frontend_report**Description:** Update an existing user's details and media (Requires Admin permissions).

frontend_report#### `create_user_address`
frontend_report**Arguments:** `(input: CreateUserAddressInput)`  
frontend_report**Returns:** `UserAddressType`  
frontend_report**Description:** Create a new address for the currently authenticated user.

frontend_report#### `update_user_address`
frontend_report**Arguments:** `(id: uuid.UUID, input: UpdateUserAddressInput)`  
frontend_report**Returns:** `UserAddressType`  
frontend_report**Description:** Update an existing address for the currently authenticated user.

frontend_report#### `delete_user_address`
frontend_report**Arguments:** `(id: uuid.UUID)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Delete an address for the currently authenticated user.

frontend_report#### `add_to_cart`
frontend_report**Arguments:** `(product_id: uuid.UUID, quantity: int)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Add a product to the authenticated user's cart.

frontend_report#### `update_cart_item`
frontend_report**Arguments:** `(product_id: uuid.UUID, quantity: int)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Update a cart item's quantity.

frontend_report#### `remove_from_cart`
frontend_report**Arguments:** `(product_id: uuid.UUID)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Remove a product from the user's cart.

frontend_report#### `clear_cart`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Clear all items from the user's cart.

frontend_report#### `apply_coupon_to_cart`
frontend_report**Arguments:** `(code: str)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Apply a coupon code directly to the authenticated user's cart.

frontend_report#### `remove_coupon_from_cart`
frontend_report**Arguments:** `(code: str)`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Remove a coupon code from the authenticated user's cart.

frontend_report#### `clear_coupons_from_cart`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `UserCartType`  
frontend_report**Description:** Clear all coupons from the authenticated user's cart.

frontend_report#### `request_forgot_password_otp`
frontend_report**Arguments:** `(mobilenumber: str)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Trigger an SMS OTP for password reset.

frontend_report#### `reset_password_with_otp`
frontend_report**Arguments:** `(mobilenumber: str, otp: str, new_password: str)`  
frontend_report**Returns:** `bool`  
frontend_report**Description:** Verify OTP and update user's password.

frontend_report## Module: `Wallet`
frontend_report### Query: `WalletQuery`
frontend_report#### `my_wallet`
frontend_report**Arguments:** `()`  
frontend_report**Returns:** `UserWalletType`  
frontend_report**Description:** Fetch wallet of the currently authenticated user.

frontend_report### Mutation: `WalletMutation`
frontend_report#### `credit_wallet`
frontend_report**Arguments:** `(user_id: uuid.UUID, points: float, remarks: Optional[str])`  
frontend_report**Returns:** `UserWalletTransactionType`  
frontend_report**Description:** Credit points to a user's wallet (Requires Admin permissions).

frontend_report#### `debit_wallet`
frontend_report**Arguments:** `(user_id: uuid.UUID, points: float, remarks: Optional[str])`  
frontend_report**Returns:** `UserWalletTransactionType`  
frontend_report**Description:** Debit points from a user's wallet (Requires Admin permissions).

