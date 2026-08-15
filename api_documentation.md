# GraphQL API Documentation

## Queries

### `me`
**Expected Input:**
- None

**Expected Output:** `UserType`

---

### `my_addresses`
**Expected Input:**
- None

**Expected Output:** `[UserAddressType]`

---

### `address`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[UserAddressType]`

---

### `my_cart`
**Expected Input:**
- None

**Expected Output:** `UserCartType`

---

### `total_users`
**Expected Input:**
- None

**Expected Output:** `int`

---

### `tenant_users`
**Expected Input:**
- None

**Expected Output:** `[UserType]`

---

### `tenant`
**Expected Input:**
- None

**Expected Output:** `[TenantType]`

---

### `products`
**Expected Input:**
- `product_type`: [ProductTypeEnum]
- `search`: [str]

**Expected Output:** `[ProductType]`

---

### `product`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[ProductType]`

---

### `attributes`
**Expected Input:**
- None

**Expected Output:** `[AttributeType]`

---

### `attribute`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[AttributeType]`

---

### `attribute_values`
**Expected Input:**
- `attribute_id`: UUID

**Expected Output:** `[AttributeValueType]`

---

### `product_groups`
**Expected Input:**
- None

**Expected Output:** `[ProductGroupType]`

---

### `product_group`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[ProductGroupType]`

---

### `categories`
**Expected Input:**
- `search`: [str]

**Expected Output:** `[CategoryType]`

---

### `category`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[CategoryType]`

---

### `pricing_types`
**Expected Input:**
- None

**Expected Output:** `[PricingTypeType]`

---

### `product_prices`
**Expected Input:**
- `product_id`: UUID

**Expected Output:** `[ProductPriceType]`

---

### `product_pricing_rules`
**Expected Input:**
- `product_id`: UUID

**Expected Output:** `[ProductPricingRuleType]`

---

### `media_list`
**Expected Input:**
- `entity_name`: [str]
- `entity_id`: [UUID]

**Expected Output:** `[MediaType]`

---

### `media`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[MediaType]`

---

### `coupon`
**Expected Input:**
- `code`: str

**Expected Output:** `[CouponType]`

---

### `coupons`
**Expected Input:**
- None

**Expected Output:** `[CouponType]`

---

### `simulate_coupon`
**Expected Input:**
- `code`: str

**Expected Output:** `CartDiscountResult`

---

### `delivery_quotes`
**Expected Input:**
- `address_id`: UUID

**Expected Output:** `[DeliveryOptionType]`

---

### `my_orders`
**Expected Input:**
- None

**Expected Output:** `[OrderType]`

---

### `order`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[OrderType]`

---

### `tenant_orders`
**Expected Input:**
- `status`: [str]

**Expected Output:** `[OrderType]`

---

### `product_reviews`
**Expected Input:**
- `product_id`: UUID

**Expected Output:** `[ProductReviewType]`

---

### `order_reviews`
**Expected Input:**
- `order_id`: UUID

**Expected Output:** `[OrderReviewType]`

---

### `company_reviews`
**Expected Input:**
- `tenant_id`: UUID

**Expected Output:** `[CompanyReviewType]`

---

### `admin_product_reviews`
**Expected Input:**
- None

**Expected Output:** `[ProductReviewType]`

---

### `admin_order_reviews`
**Expected Input:**
- None

**Expected Output:** `[OrderReviewType]`

---

### `admin_company_reviews`
**Expected Input:**
- None

**Expected Output:** `[CompanyReviewType]`

---

### `my_wallet`
**Expected Input:**
- None

**Expected Output:** `UserWalletType`

---

### `my_referral`
**Expected Input:**
- None

**Expected Output:** `[UserReferralType]`

---

### `platform_gateways`
**Expected Input:**
- None

**Expected Output:** `[PaymentGatewayType]`

---

### `active_platform_gateway`
**Expected Input:**
- None

**Expected Output:** `[PaymentGatewayType]`

---

### `tenant_gateways`
**Expected Input:**
- None

**Expected Output:** `[TenantPaymentGatewayType]`

---

### `tenant_commission`
**Expected Input:**
- None

**Expected Output:** `[TenantCommissionType]`

---

### `get_subscription_plans`
**Expected Input:**
- `active_only`: [bool]

**Expected Output:** `[SubscriptionPlanType]`

---

### `get_subscription_plan_by_id`
**Expected Input:**
- `id`: UUID

**Expected Output:** `[SubscriptionPlanType]`

---

### `get_tenant_subscription`
**Expected Input:**
- None

**Expected Output:** `[TenantSubscriptionType]`

---

### `get_subscription_features`
**Expected Input:**
- None

**Expected Output:** `[SubscriptionFeaturesType]`

---

### `get_tenant_subscription_payments`
**Expected Input:**
- `tenant_subscription_id`: UUID

**Expected Output:** `[TenantSubscriptionPaymentType]`

---

### `published_homepage`
**Expected Input:**
- None

**Expected Output:** `JSON`

---

### `homepage_config`
**Expected Input:**
- None

**Expected Output:** `HomepageConfigType`

---

## Mutations

### `create_user`
**Expected Input:**
- `input`: CreateUserInput

**Expected Output:** `UserType`

---

### `create_system_super_admin`
**Expected Input:**
- `input`: CreateSuperAdminInput

**Expected Output:** `UserType`

---

### `update_user`
**Expected Input:**
- `id`: UUID
- `input`: UpdateUserInput

**Expected Output:** `UserType`

---

### `create_user_address`
**Expected Input:**
- `input`: CreateUserAddressInput

**Expected Output:** `UserAddressType`

---

### `update_user_address`
**Expected Input:**
- `id`: UUID
- `input`: UpdateUserAddressInput

**Expected Output:** `UserAddressType`

---

### `delete_user_address`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `add_to_cart`
**Expected Input:**
- `product_id`: UUID
- `quantity`: int

**Expected Output:** `UserCartType`

---

### `update_cart_item`
**Expected Input:**
- `product_id`: UUID
- `quantity`: int

**Expected Output:** `UserCartType`

---

### `remove_from_cart`
**Expected Input:**
- `product_id`: UUID

**Expected Output:** `UserCartType`

---

### `clear_cart`
**Expected Input:**
- None

**Expected Output:** `UserCartType`

---

### `apply_coupon_to_cart`
**Expected Input:**
- `code`: str

**Expected Output:** `UserCartType`

---

### `remove_coupon_from_cart`
**Expected Input:**
- `code`: str

**Expected Output:** `UserCartType`

---

### `clear_coupons_from_cart`
**Expected Input:**
- None

**Expected Output:** `UserCartType`

---

### `request_forgot_password_otp`
**Expected Input:**
- `mobilenumber`: str

**Expected Output:** `bool`

---

### `reset_password_with_otp`
**Expected Input:**
- `mobilenumber`: str
- `otp`: str
- `new_password`: str

**Expected Output:** `bool`

---

### `create_tenant`
**Expected Input:**
- `input`: CreateTenantInput

**Expected Output:** `TenantType`

---

### `send_otp`
**Expected Input:**
- `mobilenumber`: str

**Expected Output:** `SendOtpResult`

---

### `login_with_otp`
**Expected Input:**
- `mobilenumber`: str
- `otp`: str

**Expected Output:** `AuthPayload`

---

### `login_with_password`
**Expected Input:**
- `email_or_mobile`: str
- `password`: str

**Expected Output:** `AuthPayload`

---

### `refresh_token`
**Expected Input:**
- `refresh_token`: str

**Expected Output:** `AuthTokensType`

---

### `create_product`
**Expected Input:**
- `input`: CreateProductInput

**Expected Output:** `ProductType`

---

### `update_product`
**Expected Input:**
- `id`: UUID
- `input`: UpdateProductInput

**Expected Output:** `ProductType`

---

### `delete_product`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `create_attribute`
**Expected Input:**
- `input`: CreateAttributeInput

**Expected Output:** `AttributeType`

---

### `update_attribute`
**Expected Input:**
- `id`: UUID
- `input`: UpdateAttributeInput

**Expected Output:** `AttributeType`

---

### `delete_attribute`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `create_attribute_value`
**Expected Input:**
- `input`: CreateAttributeValueInput

**Expected Output:** `AttributeValueType`

---

### `update_attribute_value`
**Expected Input:**
- `id`: UUID
- `input`: UpdateAttributeValueInput

**Expected Output:** `AttributeValueType`

---

### `delete_attribute_value`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `assign_attribute_value_to_product`
**Expected Input:**
- `product_id`: UUID
- `attribute_value_id`: UUID
- `pricing_type_id`: [UUID]

**Expected Output:** `ProductAttributeValueType`

---

### `remove_attribute_value_from_product`
**Expected Input:**
- `product_id`: UUID
- `attribute_value_id`: UUID

**Expected Output:** `bool`

---

### `create_product_group`
**Expected Input:**
- `input`: CreateProductGroupInput

**Expected Output:** `ProductGroupType`

---

### `update_product_group`
**Expected Input:**
- `id`: UUID
- `input`: UpdateProductGroupInput

**Expected Output:** `ProductGroupType`

---

### `delete_product_group`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `link_product_to_group`
**Expected Input:**
- `product_id`: UUID
- `group_id`: UUID

**Expected Output:** `ProductGroupLinkType`

---

### `unlink_product_from_group`
**Expected Input:**
- `product_id`: UUID
- `group_id`: UUID

**Expected Output:** `bool`

---

### `update_product_stock`
**Expected Input:**
- `product_id`: UUID
- `stock`: int

**Expected Output:** `ProductStockType`

---

### `create_category`
**Expected Input:**
- `input`: CreateCategoryInput

**Expected Output:** `CategoryType`

---

### `update_category`
**Expected Input:**
- `id`: UUID
- `input`: UpdateCategoryInput

**Expected Output:** `CategoryType`

---

### `delete_category`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `set_product_categories`
**Expected Input:**
- `product_id`: UUID
- `category_ids`: [UUID]

**Expected Output:** `[CategoryType]`

---

### `create_pricing_type`
**Expected Input:**
- `input`: CreatePricingTypeInput

**Expected Output:** `PricingTypeType`

---

### `update_pricing_type`
**Expected Input:**
- `id`: UUID
- `input`: UpdatePricingTypeInput

**Expected Output:** `PricingTypeType`

---

### `delete_pricing_type`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `set_product_price`
**Expected Input:**
- `input`: SetProductPriceInput

**Expected Output:** `ProductPriceType`

---

### `delete_product_price`
**Expected Input:**
- `product_id`: UUID
- `pricing_type_id`: UUID

**Expected Output:** `bool`

---

### `create_product_pricing_rule`
**Expected Input:**
- `input`: CreateProductPricingRuleInput

**Expected Output:** `ProductPricingRuleType`

---

### `delete_product_pricing_rule`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `create_media`
**Expected Input:**
- `input`: CreateMediaInput

**Expected Output:** `MediaType`

---

### `update_media`
**Expected Input:**
- `id`: UUID
- `input`: UpdateMediaInput

**Expected Output:** `MediaType`

---

### `delete_media`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `create_coupon`
**Expected Input:**
- `input`: CreateCouponInput

**Expected Output:** `CouponType`

---

### `update_coupon_status`
**Expected Input:**
- `id`: UUID
- `is_active`: bool

**Expected Output:** `CouponType`

---

### `apply_coupon`
**Expected Input:**
- `code`: str
- `order_id`: UUID

**Expected Output:** `CartDiscountResult`

---

### `select_delivery_option`
**Expected Input:**
- `address_id`: UUID
- `service_name`: str

**Expected Output:** `UserCartType`

---

### `checkout_cart`
**Expected Input:**
- `payment_method`: str

**Expected Output:** `OrderType`

---

### `record_payment`
**Expected Input:**
- `order_id`: UUID
- `amount`: float
- `payment_method`: str
- `transaction_reference`: [str]
- `status`: str

**Expected Output:** `OrderPaymentType`

---

### `request_order_return`
**Expected Input:**
- `input`: RequestReturnInput

**Expected Output:** `OrderReturnType`

---

### `approve_order_return`
**Expected Input:**
- `return_id`: UUID
- `approved`: bool

**Expected Output:** `OrderReturnType`

---

### `complete_order_return`
**Expected Input:**
- `return_id`: UUID
- `refund_amount`: float

**Expected Output:** `OrderReturnType`

---

### `create_product_review`
**Expected Input:**
- `input`: CreateProductReviewInput

**Expected Output:** `ProductReviewType`

---

### `create_order_review`
**Expected Input:**
- `input`: CreateOrderReviewInput

**Expected Output:** `OrderReviewType`

---

### `create_company_review`
**Expected Input:**
- `input`: CreateCompanyReviewInput

**Expected Output:** `CompanyReviewType`

---

### `update_product_review_status`
**Expected Input:**
- `id`: UUID
- `status`: str

**Expected Output:** `ProductReviewType`

---

### `update_order_review_status`
**Expected Input:**
- `id`: UUID
- `status`: str

**Expected Output:** `OrderReviewType`

---

### `update_company_review_status`
**Expected Input:**
- `id`: UUID
- `status`: str

**Expected Output:** `CompanyReviewType`

---

### `credit_wallet`
**Expected Input:**
- `user_id`: UUID
- `points`: float
- `remarks`: [str]

**Expected Output:** `UserWalletTransactionType`

---

### `debit_wallet`
**Expected Input:**
- `user_id`: UUID
- `points`: float
- `remarks`: [str]

**Expected Output:** `UserWalletTransactionType`

---

### `generate_referral_code`
**Expected Input:**
- `custom_code`: [str]

**Expected Output:** `UserReferralType`

---

### `claim_referral`
**Expected Input:**
- `input`: ClaimReferralInput

**Expected Output:** `UserReferralHistoryType`

---

### `configure_platform_gateway`
**Expected Input:**
- `input`: ConfigurePlatformGatewayInput

**Expected Output:** `PaymentGatewayType`

---

### `activate_platform_gateway`
**Expected Input:**
- `id`: UUID

**Expected Output:** `PaymentGatewayType`

---

### `configure_tenant_gateway`
**Expected Input:**
- `input`: ConfigureTenantGatewayInput

**Expected Output:** `TenantPaymentGatewayType`

---

### `activate_tenant_gateway`
**Expected Input:**
- `id`: UUID

**Expected Output:** `TenantPaymentGatewayType`

---

### `configure_tenant_commission`
**Expected Input:**
- `input`: ConfigureTenantCommissionInput

**Expected Output:** `TenantCommissionType`

---

### `initiate_online_payment`
**Expected Input:**
- `order_id`: UUID

**Expected Output:** `InitiatePaymentResult`

---

### `initiate_cart_payment`
**Expected Input:**
- None

**Expected Output:** `InitiatePaymentResult`

---

### `create_subscription_plan`
**Expected Input:**
- `input`: CreateSubscriptionPlanInput

**Expected Output:** `SubscriptionPlanType`

---

### `update_subscription_plan`
**Expected Input:**
- `id`: UUID
- `input`: UpdateSubscriptionPlanInput

**Expected Output:** `SubscriptionPlanType`

---

### `delete_subscription_plan`
**Expected Input:**
- `id`: UUID

**Expected Output:** `bool`

---

### `create_subscription_features`
**Expected Input:**
- `input`: CreateSubscriptionFeaturesInput

**Expected Output:** `SubscriptionFeaturesType`

---

### `update_subscription_features`
**Expected Input:**
- `plan_id`: UUID
- `input`: UpdateSubscriptionFeaturesInput

**Expected Output:** `SubscriptionFeaturesType`

---

### `subscribe_tenant`
**Expected Input:**
- `input`: SubscribeTenantInput

**Expected Output:** `TenantSubscriptionType`

---

### `renew_tenant_subscription`
**Expected Input:**
- `input`: RenewTenantSubscriptionInput

**Expected Output:** `TenantSubscriptionType`

---

### `cancel_tenant_subscription`
**Expected Input:**
- `remark`: [str]

**Expected Output:** `TenantSubscriptionType`

---

### `create_tenant_subscription_payment`
**Expected Input:**
- `input`: CreateTenantSubscriptionPaymentInput

**Expected Output:** `TenantSubscriptionPaymentType`

---

### `create_or_update_homepage_config`
**Expected Input:**
- `input`: CreateOrUpdateHomepageConfigInput

**Expected Output:** `HomepageConfigType`

---

### `update_homepage_config`
**Expected Input:**
- `input`: UpdateHomepageConfigInput

**Expected Output:** `HomepageConfigType`

---

### `delete_homepage_section`
**Expected Input:**
- `section_id`: UUID

**Expected Output:** `bool`

---

## Object Types

### `UserType`
**Fields:**
- `id`: UUID
- `name`: str
- `mobilenumber`: str
- `email`: [str]
- `status`: UserStatus
- `role`: UserRole
- `tenant_id`: [UUID]
- `created_at`: datetime
- `updated_at`: datetime
- `tenant`: [TenantType]
- `wallet`: LazyType(type_name='UserWalletType', module='app.wallet.graphql', package=None)
- `referral`: [LazyType(type_name='UserReferralType', module='app.referral.graphql', package=None)]
- `addresses`: [UserAddressType]
- `media`: [MediaType]
- `cart`: [UserCartType]

### `UserAddressType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `address_line_1`: str
- `address_line_2`: [str]
- `landmark`: [str]
- `pincode`: str
- `state`: str
- `district`: str
- `customer_name`: str
- `phone_number`: str
- `is_primary`: bool
- `lat_long`: [str]
- `third_party_app_address`: [str]
- `created_at`: datetime
- `updated_at`: datetime

### `UserCartType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `delivery_fee`: [float]
- `delivery_service`: [str]
- `estimated_days`: [int]
- `delivery_address_id`: [UUID]
- `created_at`: datetime
- `updated_at`: datetime
- `items`: [CartItemType]
- `applied_coupons`: [CouponType]
- `delivery_address`: [UserAddressType]
- `bill_summary`: BillSummaryType

### `TenantType`
**Fields:**
- `id`: UUID
- `created_at`: datetime
- `updated_at`: datetime
- `business_name`: str

### `ProductType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `parent_id`: [UUID]
- `title`: str
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `product_type`: ProductTypeEnum
- `thumbnail_media_id`: [UUID]
- `created_at`: datetime
- `updated_at`: datetime
- `parent`: [ProductType]
- `children`: [ProductType]
- `price`: [float]
- `effective_price`: float
- `prices`: [LazyType(type_name='ProductPriceType', module='app.products.pricing.graphql', package=None)]
- `thumbnail`: [MediaType]
- `media`: [MediaType]
- `categories`: [LazyType(type_name='CategoryType', module='app.products.categories.graphql', package=None)]
- `attributes`: [ProductAttributeValueType]
- `groups`: [ProductGroupLinkType]
- `related_products`: [ProductType]
- `stock`: int
- `reviews`: [LazyType(type_name='ProductReviewType', module='app.reviews.graphql', package=None)]
- `pricing_rules`: [LazyType(type_name='ProductPricingRuleType', module='app.products.pricing.graphql', package=None)]

### `ProductTypeEnum`

### `AttributeType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `name`: str
- `display_name`: str
- `created_at`: datetime
- `values`: [AttributeValueType]

### `AttributeValueType`
**Fields:**
- `id`: UUID
- `attribute_id`: UUID
- `value`: str
- `hex_code`: [str]
- `created_at`: datetime
- `attribute`: AttributeType

### `ProductGroupType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `name`: str
- `description`: [str]
- `created_at`: datetime
- `updated_at`: datetime
- `products`: [ProductType]

### `CategoryType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `parent_id`: [UUID]
- `title`: str
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `thumbnail_media_id`: [UUID]
- `created_at`: datetime
- `updated_at`: datetime
- `parent`: [CategoryType]
- `children`: [CategoryType]
- `products`: [LazyType(type_name='ProductType', module='app.products.products.graphql', package=None)]
- `thumbnail`: [MediaType]
- `media`: [MediaType]

### `PricingTypeType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `type`: str
- `created_at`: datetime
- `updated_at`: datetime

### `ProductPriceType`
**Fields:**
- `id`: UUID
- `product_id`: UUID
- `pricing_type_id`: UUID
- `price`: float
- `created_at`: datetime
- `updated_at`: datetime
- `pricing_type`: PricingTypeType

### `ProductPricingRuleType`
**Fields:**
- `id`: UUID
- `product_id`: UUID
- `name`: str
- `priority`: int
- `rule_type`: str
- `value`: float
- `min_quantity`: [int]
- `max_quantity`: [int]
- `location_id`: [UUID]
- `pincode`: [str]
- `start_time`: [datetime]
- `end_time`: [datetime]
- `day_of_week`: [int]
- `start_hour`: [int]
- `end_hour`: [int]
- `min_stock`: [int]
- `max_stock`: [int]
- `pricing_type_id`: [UUID]
- `created_at`: datetime
- `updated_at`: datetime
- `pricing_type`: [PricingTypeType]

### `MediaType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `entity_name`: [str]
- `entity_id`: [UUID]
- `file_path`: str
- `media_url`: str
- `media_type`: MediaTypeEnum
- `file_extension`: [str]
- `alt_text`: [str]
- `meta_attributes`: [JSON]
- `created_at`: datetime
- `updated_at`: datetime

### `CouponType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `code`: str
- `description`: [str]
- `discount_type`: str
- `discount_value`: float
- `min_order_value`: float
- `max_discount_amount`: [float]
- `start_date`: datetime
- `end_date`: datetime
- `usage_limit_total`: [int]
- `usage_limit_per_user`: int
- `usage_count`: int
- `is_active`: bool
- `rules`: JSON

### `CartDiscountResult`
**Fields:**
- `is_valid`: bool
- `error_message`: [str]
- `discount_applied`: float
- `new_total`: float
- `original_total`: float

### `DeliveryOptionType`
**Fields:**
- `service_name`: str
- `delivery_fee`: float
- `estimated_days`: int

### `OrderType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `delivery_address_id`: [UUID]
- `delivery_service`: [str]
- `delivery_fee`: float
- `estimated_days`: [int]
- `item_total`: float
- `discount_applied`: float
- `tax`: float
- `grand_total`: float
- `order_status`: str
- `payment_status`: str
- `applied_coupons`: [str]
- `created_at`: datetime
- `updated_at`: datetime
- `items`: [OrderItemType]
- `payments`: [OrderPaymentType]
- `returns`: [OrderReturnType]
- `delivery_address`: [UserAddressType]

### `ProductReviewType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `product_id`: UUID
- `rating_points`: int
- `review`: [str]
- `status`: str
- `created_at`: datetime
- `updated_at`: datetime
- `user`: [LazyType(type_name='UserType', module='app.users.graphql', package=None)]

### `OrderReviewType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `order_id`: UUID
- `rating_points`: int
- `review`: [str]
- `status`: str
- `created_at`: datetime
- `updated_at`: datetime
- `user`: [LazyType(type_name='UserType', module='app.users.graphql', package=None)]

### `CompanyReviewType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `tenant_id`: UUID
- `rating_points`: int
- `review`: [str]
- `status`: str
- `created_at`: datetime
- `updated_at`: datetime
- `user`: [LazyType(type_name='UserType', module='app.users.graphql', package=None)]

### `UserWalletType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `points`: float
- `created_at`: datetime
- `updated_at`: datetime
- `transactions`: [UserWalletTransactionType]

### `UserReferralType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `referral_points`: float
- `referral_code`: str
- `created_at`: datetime
- `updated_at`: datetime
- `histories`: [UserReferralHistoryType]
- `transactions`: [UserReferralPointsTransactionHistoryType]

### `PaymentGatewayType`
**Fields:**
- `id`: UUID
- `name`: str
- `credentials`: JSON
- `webhook_secret`: [str]
- `is_active`: bool

### `TenantPaymentGatewayType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `gateway_id`: UUID
- `credentials`: JSON
- `webhook_secret`: [str]
- `is_active`: bool

### `TenantCommissionType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `commission_percent`: float
- `linked_account_id`: str

### `SubscriptionPlanType`
**Fields:**
- `id`: UUID
- `title`: str
- `description`: [str]
- `price`: float
- `billing_cycle`: str
- `type`: str
- `is_active`: bool
- `created_at`: datetime
- `updated_at`: datetime
- `features`: [SubscriptionFeaturesType]

### `TenantSubscriptionType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `plan_id`: UUID
- `plan_title_snapshot`: str
- `plan_price_snapshot`: float
- `status`: str
- `start_date`: datetime
- `end_date`: datetime
- `coupon_id`: [UUID]
- `amount`: float
- `remark`: [str]
- `created_at`: datetime
- `updated_at`: datetime
- `plan`: [SubscriptionPlanType]
- `features`: [SubscriptionFeaturesType]
- `payments`: [TenantSubscriptionPaymentType]

### `SubscriptionFeaturesType`
**Fields:**
- `id`: UUID
- `plan_id`: UUID
- `user_limit`: [int]
- `product_limit`: [int]
- `coupon_limit`: [int]
- `cod_enabled`: bool
- `cms_enabled`: bool
- `otp_login_enabled`: bool
- `custom_domain_enabled`: bool
- `created_at`: datetime
- `updated_at`: datetime

### `TenantSubscriptionPaymentType`
**Fields:**
- `id`: UUID
- `tenant_subscription_id`: UUID
- `amount`: float
- `transaction_id`: [str]
- `payment_method`: str
- `status`: str
- `paid_at`: [datetime]
- `created_at`: datetime

### `HomepageConfigType`
**Fields:**
- `tenant_id`: UUID
- `version`: int
- `status`: str
- `sections`: [HomepageSectionType]
- `created_at`: datetime
- `updated_at`: datetime

### `UserStatus`

### `UserRole`

### `UserWalletTransactionType`
**Fields:**
- `id`: UUID
- `user_id`: UUID
- `wallet_id`: UUID
- `points`: float
- `type`: str
- `payment_id`: [UUID]
- `order_id`: [UUID]
- `remarks`: [str]
- `created_at`: datetime

### `UserReferralHistoryType`
**Fields:**
- `id`: UUID
- `referral_user_id`: UUID
- `referrer_user_id`: UUID
- `referred_entity`: str
- `referred_entity_id`: [UUID]
- `points`: float
- `created_at`: datetime
- `referral_user`: [LazyType(type_name='UserType', module='app.users.graphql', package=None)]
- `referrer_user`: [LazyType(type_name='UserType', module='app.users.graphql', package=None)]

### `UserReferralPointsTransactionHistoryType`
**Fields:**
- `id`: UUID
- `user_referral_id`: UUID
- `wallet_id`: UUID
- `points`: float
- `type`: str
- `payment_id`: [UUID]
- `order_id`: [UUID]
- `remarks`: [str]
- `created_at`: datetime

### `MediaTypeEnum`

### `CartItemType`
**Fields:**
- `id`: UUID
- `cart_id`: UUID
- `user_id`: UUID
- `product_id`: UUID
- `quantity`: int
- `created_at`: datetime
- `updated_at`: datetime
- `product`: ProductType

### `BillSummaryType`
**Fields:**
- `item_total`: float
- `discount_applied`: float
- `delivery_fee`: float
- `tax`: float
- `grand_total`: float

### `ProductAttributeValueType`
**Fields:**
- `id`: UUID
- `product_id`: UUID
- `attribute_value_id`: UUID
- `pricing_type_id`: [UUID]
- `created_at`: datetime
- `attribute_value`: AttributeValueType
- `pricing_type`: [LazyType(type_name='PricingTypeType', module='app.products.pricing.graphql', package=None)]

### `ProductGroupLinkType`
**Fields:**
- `id`: UUID
- `product_id`: UUID
- `group_id`: UUID
- `created_at`: datetime
- `group`: ProductGroupType

### `OrderItemType`
**Fields:**
- `id`: UUID
- `order_id`: UUID
- `product_id`: UUID
- `quantity`: int
- `unit_price`: float
- `discount_applied`: float
- `subtotal`: float
- `product`: ProductType

### `OrderPaymentType`
**Fields:**
- `id`: UUID
- `order_id`: UUID
- `amount`: float
- `payment_method`: str
- `status`: str
- `transaction_reference`: [str]
- `gateway_response`: JSON
- `created_at`: datetime

### `OrderReturnType`
**Fields:**
- `id`: UUID
- `order_id`: UUID
- `reason`: str
- `status`: str
- `refund_status`: str
- `refund_amount`: float
- `created_at`: datetime
- `items`: [OrderReturnItemType]

### `OrderReturnItemType`
**Fields:**
- `id`: UUID
- `order_return_id`: UUID
- `order_item_id`: UUID
- `quantity`: int
- `condition`: str

### `HomepageSectionType`
**Fields:**
- `id`: UUID
- `type`: str
- `title`: str
- `order`: int
- `config`: JSON

### `SendOtpResult`
**Fields:**
- `success`: bool
- `message`: str
- `otp`: [str]

### `AuthPayload`
**Fields:**
- `tokens`: AuthTokensType
- `user`: UserType

### `AuthTokensType`
**Fields:**
- `access_token`: str
- `refresh_token`: str
- `token_type`: str

### `ProductStockType`
**Fields:**
- `id`: UUID
- `tenant_id`: UUID
- `product_id`: UUID
- `stock`: int
- `created_at`: datetime
- `updated_at`: datetime

### `InitiatePaymentResult`
**Fields:**
- `key`: str
- `amount`: int
- `currency`: str
- `name`: str
- `order_id`: str
- `payment_id`: str

## Input Types

### `CreateUserInput`
**Fields:**
- `name`: str
- `mobilenumber`: str
- `email`: [str]
- `password`: [str]
- `role`: UserRole
- `media`: [[CreateMediaInput]]

### `CreateSuperAdminInput`
**Fields:**
- `name`: str
- `mobilenumber`: str
- `email`: [str]
- `password`: [str]
- `media`: [[CreateMediaInput]]

### `UpdateUserInput`
**Fields:**
- `name`: [str]
- `mobilenumber`: [str]
- `email`: [str]
- `password`: [str]
- `role`: [UserRole]
- `status`: [UserStatus]
- `media`: [[CreateMediaInput]]

### `CreateUserAddressInput`
**Fields:**
- `address_line_1`: str
- `address_line_2`: [str]
- `landmark`: [str]
- `pincode`: str
- `state`: str
- `district`: str
- `customer_name`: str
- `phone_number`: str
- `is_primary`: bool
- `lat_long`: [str]
- `third_party_app_address`: [str]

### `UpdateUserAddressInput`
**Fields:**
- `address_line_1`: [str]
- `address_line_2`: [str]
- `landmark`: [str]
- `pincode`: [str]
- `state`: [str]
- `district`: [str]
- `customer_name`: [str]
- `phone_number`: [str]
- `is_primary`: [bool]
- `lat_long`: [str]
- `third_party_app_address`: [str]

### `CreateTenantInput`
**Fields:**
- `business_name`: str
- `admin_name`: str
- `admin_email`: [str]
- `admin_mobile`: str
- `admin_password`: [str]

### `CreateProductInput`
**Fields:**
- `title`: str
- `product_type`: ProductTypeEnum
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `parent_id`: [UUID]
- `thumbnail_media_id`: [UUID]
- `media`: [[CreateMediaInput]]

### `UpdateProductInput`
**Fields:**
- `title`: [str]
- `product_type`: [ProductTypeEnum]
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `parent_id`: [UUID]
- `thumbnail_media_id`: [UUID]
- `media`: [[CreateMediaInput]]

### `CreateAttributeInput`
**Fields:**
- `name`: str
- `display_name`: str

### `UpdateAttributeInput`
**Fields:**
- `name`: str
- `display_name`: str

### `CreateAttributeValueInput`
**Fields:**
- `attribute_id`: UUID
- `value`: str
- `hex_code`: [str]

### `UpdateAttributeValueInput`
**Fields:**
- `value`: [str]
- `hex_code`: [str]

### `CreateProductGroupInput`
**Fields:**
- `name`: str
- `description`: [str]

### `UpdateProductGroupInput`
**Fields:**
- `name`: [str]
- `description`: [str]

### `CreateCategoryInput`
**Fields:**
- `title`: str
- `parent_id`: [UUID]
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `thumbnail_media_id`: [UUID]
- `media`: [[CreateMediaInput]]

### `UpdateCategoryInput`
**Fields:**
- `title`: [str]
- `parent_id`: [UUID]
- `subtitle`: [str]
- `description`: [str]
- `description_long`: [str]
- `sku`: [str]
- `thumbnail_media_id`: [UUID]
- `media`: [[CreateMediaInput]]

### `CreatePricingTypeInput`
**Fields:**
- `type`: str

### `UpdatePricingTypeInput`
**Fields:**
- `type`: str

### `SetProductPriceInput`
**Fields:**
- `product_id`: UUID
- `pricing_type_id`: UUID
- `price`: float

### `CreateProductPricingRuleInput`
**Fields:**
- `product_id`: UUID
- `name`: str
- `priority`: int
- `rule_type`: str
- `value`: float
- `min_quantity`: [int]
- `max_quantity`: [int]
- `location_id`: [UUID]
- `pincode`: [str]
- `start_time`: [datetime]
- `end_time`: [datetime]
- `day_of_week`: [int]
- `start_hour`: [int]
- `end_hour`: [int]
- `min_stock`: [int]
- `max_stock`: [int]
- `pricing_type_id`: [UUID]

### `CreateMediaInput`
**Fields:**
- `file_path`: str
- `media_url`: str
- `media_type`: MediaTypeEnum
- `file_extension`: [str]
- `alt_text`: [str]
- `meta_attributes`: [JSON]
- `entity_name`: [str]
- `entity_id`: [UUID]

### `UpdateMediaInput`
**Fields:**
- `file_path`: [str]
- `media_url`: [str]
- `media_type`: [MediaTypeEnum]
- `file_extension`: [str]
- `alt_text`: [str]
- `meta_attributes`: [JSON]
- `entity_name`: [str]
- `entity_id`: [UUID]

### `CreateCouponInput`
**Fields:**
- `code`: str
- `discount_type`: str
- `discount_value`: float
- `start_date`: datetime
- `end_date`: datetime
- `description`: [str]
- `min_order_value`: float
- `max_discount_amount`: [float]
- `usage_limit_total`: [int]
- `usage_limit_per_user`: int
- `rules`: [JSON]

### `RequestReturnInput`
**Fields:**
- `order_id`: UUID
- `reason`: str
- `items`: [ReturnItemInput]

### `CreateProductReviewInput`
**Fields:**
- `product_id`: UUID
- `rating_points`: int
- `review`: [str]

### `CreateOrderReviewInput`
**Fields:**
- `order_id`: UUID
- `rating_points`: int
- `review`: [str]

### `CreateCompanyReviewInput`
**Fields:**
- `tenant_id`: UUID
- `rating_points`: int
- `review`: [str]

### `ClaimReferralInput`
**Fields:**
- `referrer_code`: str
- `referred_entity`: str
- `referred_entity_id`: [UUID]
- `points`: float
- `payment_id`: [UUID]
- `order_id`: [UUID]
- `remarks`: [str]

### `ConfigurePlatformGatewayInput`
**Fields:**
- `name`: str
- `credentials`: JSON
- `webhook_secret`: [str]
- `is_active`: bool

### `ConfigureTenantGatewayInput`
**Fields:**
- `gateway_id`: UUID
- `credentials`: JSON
- `webhook_secret`: [str]
- `is_active`: bool

### `ConfigureTenantCommissionInput`
**Fields:**
- `commission_percent`: float
- `linked_account_id`: str

### `CreateSubscriptionPlanInput`
**Fields:**
- `title`: str
- `price`: float
- `billing_cycle`: str
- `type`: str
- `description`: [str]
- `is_active`: [bool]

### `UpdateSubscriptionPlanInput`
**Fields:**
- `title`: [str]
- `price`: [float]
- `billing_cycle`: [str]
- `type`: [str]
- `description`: [str]
- `is_active`: [bool]

### `CreateSubscriptionFeaturesInput`
**Fields:**
- `plan_id`: UUID
- `user_limit`: [int]
- `product_limit`: [int]
- `coupon_limit`: [int]
- `cod_enabled`: [bool]
- `cms_enabled`: [bool]
- `otp_login_enabled`: [bool]
- `custom_domain_enabled`: [bool]

### `UpdateSubscriptionFeaturesInput`
**Fields:**
- `user_limit`: [int]
- `product_limit`: [int]
- `coupon_limit`: [int]
- `cod_enabled`: [bool]
- `cms_enabled`: [bool]
- `otp_login_enabled`: [bool]
- `custom_domain_enabled`: [bool]

### `SubscribeTenantInput`
**Fields:**
- `plan_id`: UUID
- `start_date`: datetime
- `end_date`: datetime
- `status`: [str]
- `coupon_id`: [UUID]
- `remark`: [str]

### `RenewTenantSubscriptionInput`
**Fields:**
- `plan_id`: UUID
- `start_date`: datetime
- `end_date`: datetime
- `coupon_id`: [UUID]
- `remark`: [str]

### `CreateTenantSubscriptionPaymentInput`
**Fields:**
- `tenant_subscription_id`: UUID
- `amount`: float
- `payment_method`: str
- `status`: [str]
- `transaction_id`: [str]
- `paid_at`: [datetime]

### `CreateOrUpdateHomepageConfigInput`
**Fields:**
- `status`: str
- `sections`: [HomepageSectionInput]

### `UpdateHomepageConfigInput`
**Fields:**
- `status`: [str]
- `sections`: [[HomepageSectionInput]]

### `ReturnItemInput`
**Fields:**
- `order_item_id`: UUID
- `quantity`: int
- `condition`: str

### `HomepageSectionInput`
**Fields:**
- `type`: str
- `title`: str
- `config`: JSON
- `id`: [UUID]
- `order`: int

