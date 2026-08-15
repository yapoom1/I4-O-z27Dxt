# Postman GraphQL API Samples

This document contains ready-to-copy sample queries and mutations for Postman.

## Queries

### me
```graphql
query {
  me {
    id
    tenant_id
  }
}
```

### my_addresses
```graphql
query {
  my_addresses {
    id
    user_id
  }
}
```

### address
```graphql
query {
  address(id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
  }
}
```

### my_cart
```graphql
query {
  my_cart {
    id
    user_id
    delivery_address_id
  }
}
```

### total_users
```graphql
query {
  total_users 
}
```

### tenant_users
```graphql
query {
  tenant_users {
    id
    tenant_id
  }
}
```

### tenant
```graphql
query {
  tenant {
    id
  }
}
```

### products
```graphql
query {
  products(product_type: [""], search: [""]) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### product
```graphql
query {
  product(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### attributes
```graphql
query {
  attributes {
    id
    tenant_id
  }
}
```

### attribute
```graphql
query {
  attribute(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
  }
}
```

### attribute_values
```graphql
query {
  attribute_values(attribute_id: "00000000-0000-0000-0000-000000000000") {
    id
    attribute_id
  }
}
```

### product_groups
```graphql
query {
  product_groups {
    id
    tenant_id
  }
}
```

### product_group
```graphql
query {
  product_group(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
  }
}
```

### categories
```graphql
query {
  categories(search: [""]) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### category
```graphql
query {
  category(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### pricing_types
```graphql
query {
  pricing_types {
    id
    tenant_id
  }
}
```

### product_prices
```graphql
query {
  product_prices(product_id: "00000000-0000-0000-0000-000000000000") {
    id
    product_id
    pricing_type_id
  }
}
```

### product_pricing_rules
```graphql
query {
  product_pricing_rules(product_id: "00000000-0000-0000-0000-000000000000") {
    id
    product_id
    location_id
    pricing_type_id
  }
}
```

### media_list
```graphql
query {
  media_list(entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    entity_id
    meta_attributes
  }
}
```

### media
```graphql
query {
  media(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    entity_id
    meta_attributes
  }
}
```

### coupon
```graphql
query {
  coupon(code: "") {
    id
    tenant_id
    rules
  }
}
```

### coupons
```graphql
query {
  coupons {
    id
    tenant_id
    rules
  }
}
```

### simulate_coupon
```graphql
query {
  simulate_coupon(code: "") 
}
```

### delivery_quotes
```graphql
query {
  delivery_quotes(address_id: "00000000-0000-0000-0000-000000000000") 
}
```

### my_orders
```graphql
query {
  my_orders {
    id
    user_id
    delivery_address_id
  }
}
```

### order
```graphql
query {
  order(id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
    delivery_address_id
  }
}
```

### tenant_orders
```graphql
query {
  tenant_orders(status: [""]) {
    id
    user_id
    delivery_address_id
  }
}
```

### product_reviews
```graphql
query {
  product_reviews(product_id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
    product_id
  }
}
```

### order_reviews
```graphql
query {
  order_reviews(order_id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
    order_id
  }
}
```

### company_reviews
```graphql
query {
  company_reviews(tenant_id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
    tenant_id
  }
}
```

### admin_product_reviews
```graphql
query {
  admin_product_reviews {
    id
    user_id
    product_id
  }
}
```

### admin_order_reviews
```graphql
query {
  admin_order_reviews {
    id
    user_id
    order_id
  }
}
```

### admin_company_reviews
```graphql
query {
  admin_company_reviews {
    id
    user_id
    tenant_id
  }
}
```

### my_wallet
```graphql
query {
  my_wallet {
    id
    user_id
  }
}
```

### my_referral
```graphql
query {
  my_referral {
    id
    user_id
  }
}
```

### platform_gateways
```graphql
query {
  platform_gateways {
    id
    credentials
  }
}
```

### active_platform_gateway
```graphql
query {
  active_platform_gateway {
    id
    credentials
  }
}
```

### tenant_gateways
```graphql
query {
  tenant_gateways {
    id
    tenant_id
    gateway_id
    credentials
  }
}
```

### tenant_commission
```graphql
query {
  tenant_commission {
    id
    tenant_id
  }
}
```

### get_subscription_plans
```graphql
query {
  get_subscription_plans(active_only: [""]) {
    id
  }
}
```

### get_subscription_plan_by_id
```graphql
query {
  get_subscription_plan_by_id(id: "00000000-0000-0000-0000-000000000000") {
    id
  }
}
```

### get_tenant_subscription
```graphql
query {
  get_tenant_subscription {
    id
    tenant_id
    plan_id
    coupon_id
  }
}
```

### get_subscription_features
```graphql
query {
  get_subscription_features {
    id
    plan_id
  }
}
```

### get_tenant_subscription_payments
```graphql
query {
  get_tenant_subscription_payments(tenant_subscription_id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_subscription_id
  }
}
```

### published_homepage
```graphql
query {
  published_homepage 
}
```

### homepage_config
```graphql
query {
  homepage_config {
    tenant_id
  }
}
```

## Mutations

### create_user
```graphql
mutation {
  create_user(input: { name: "", mobilenumber: "", email: [""], password: [""], role: "", media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
  }
}
```

### create_system_super_admin
```graphql
mutation {
  create_system_super_admin(input: { name: "", mobilenumber: "", email: [""], password: [""], media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
  }
}
```

### update_user
```graphql
mutation {
  update_user(id: "00000000-0000-0000-0000-000000000000", input: { name: [""], mobilenumber: [""], email: [""], password: [""], role: [""], status: [""], media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
  }
}
```

### create_user_address
```graphql
mutation {
  create_user_address(input: { address_line_1: "", address_line_2: [""], landmark: [""], pincode: "", state: "", district: "", customer_name: "", phone_number: "", is_primary: "", lat_long: [""], third_party_app_address: [""] }) {
    id
    user_id
  }
}
```

### update_user_address
```graphql
mutation {
  update_user_address(id: "00000000-0000-0000-0000-000000000000", input: { address_line_1: [""], address_line_2: [""], landmark: [""], pincode: [""], state: [""], district: [""], customer_name: [""], phone_number: [""], is_primary: [""], lat_long: [""], third_party_app_address: [""] }) {
    id
    user_id
  }
}
```

### delete_user_address
```graphql
mutation {
  delete_user_address(id: "00000000-0000-0000-0000-000000000000") 
}
```

### add_to_cart
```graphql
mutation {
  add_to_cart(product_id: "00000000-0000-0000-0000-000000000000", quantity: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### update_cart_item
```graphql
mutation {
  update_cart_item(product_id: "00000000-0000-0000-0000-000000000000", quantity: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### remove_from_cart
```graphql
mutation {
  remove_from_cart(product_id: "00000000-0000-0000-0000-000000000000") {
    id
    user_id
    delivery_address_id
  }
}
```

### clear_cart
```graphql
mutation {
  clear_cart {
    id
    user_id
    delivery_address_id
  }
}
```

### apply_coupon_to_cart
```graphql
mutation {
  apply_coupon_to_cart(code: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### remove_coupon_from_cart
```graphql
mutation {
  remove_coupon_from_cart(code: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### clear_coupons_from_cart
```graphql
mutation {
  clear_coupons_from_cart {
    id
    user_id
    delivery_address_id
  }
}
```

### request_forgot_password_otp
```graphql
mutation {
  request_forgot_password_otp(mobilenumber: "") 
}
```

### reset_password_with_otp
```graphql
mutation {
  reset_password_with_otp(mobilenumber: "", otp: "", new_password: "") 
}
```

### create_tenant
```graphql
mutation {
  create_tenant(input: { business_name: "", admin_name: "", admin_email: [""], admin_mobile: "", admin_password: [""] }) {
    id
  }
}
```

### send_otp
```graphql
mutation {
  send_otp(mobilenumber: "") 
}
```

### login_with_otp
```graphql
mutation {
  login_with_otp(mobilenumber: "", otp: "") 
}
```

### login_with_password
```graphql
mutation {
  login_with_password(email_or_mobile: "", password: "") 
}
```

### refresh_token
```graphql
mutation {
  refresh_token(refresh_token: "") 
}
```

### create_product
```graphql
mutation {
  create_product(input: { title: "", product_type: "", subtitle: [""], description: [""], description_long: [""], sku: [""], parent_id: "00000000-0000-0000-0000-000000000000", thumbnail_media_id: "00000000-0000-0000-0000-000000000000", media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### update_product
```graphql
mutation {
  update_product(id: "00000000-0000-0000-0000-000000000000", input: { title: [""], product_type: [""], subtitle: [""], description: [""], description_long: [""], sku: [""], parent_id: "00000000-0000-0000-0000-000000000000", thumbnail_media_id: "00000000-0000-0000-0000-000000000000", media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### delete_product
```graphql
mutation {
  delete_product(id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_attribute
```graphql
mutation {
  create_attribute(input: { name: "", display_name: "" }) {
    id
    tenant_id
  }
}
```

### update_attribute
```graphql
mutation {
  update_attribute(id: "00000000-0000-0000-0000-000000000000", input: { name: "", display_name: "" }) {
    id
    tenant_id
  }
}
```

### delete_attribute
```graphql
mutation {
  delete_attribute(id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_attribute_value
```graphql
mutation {
  create_attribute_value(input: { attribute_id: "00000000-0000-0000-0000-000000000000", value: "", hex_code: [""] }) {
    id
    attribute_id
  }
}
```

### update_attribute_value
```graphql
mutation {
  update_attribute_value(id: "00000000-0000-0000-0000-000000000000", input: { value: [""], hex_code: [""] }) {
    id
    attribute_id
  }
}
```

### delete_attribute_value
```graphql
mutation {
  delete_attribute_value(id: "00000000-0000-0000-0000-000000000000") 
}
```

### assign_attribute_value_to_product
```graphql
mutation {
  assign_attribute_value_to_product(product_id: "00000000-0000-0000-0000-000000000000", attribute_value_id: "00000000-0000-0000-0000-000000000000", pricing_type_id: "00000000-0000-0000-0000-000000000000") {
    id
    product_id
    attribute_value_id
    pricing_type_id
  }
}
```

### remove_attribute_value_from_product
```graphql
mutation {
  remove_attribute_value_from_product(product_id: "00000000-0000-0000-0000-000000000000", attribute_value_id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_product_group
```graphql
mutation {
  create_product_group(input: { name: "", description: [""] }) {
    id
    tenant_id
  }
}
```

### update_product_group
```graphql
mutation {
  update_product_group(id: "00000000-0000-0000-0000-000000000000", input: { name: [""], description: [""] }) {
    id
    tenant_id
  }
}
```

### delete_product_group
```graphql
mutation {
  delete_product_group(id: "00000000-0000-0000-0000-000000000000") 
}
```

### link_product_to_group
```graphql
mutation {
  link_product_to_group(product_id: "00000000-0000-0000-0000-000000000000", group_id: "00000000-0000-0000-0000-000000000000") {
    id
    product_id
    group_id
  }
}
```

### unlink_product_from_group
```graphql
mutation {
  unlink_product_from_group(product_id: "00000000-0000-0000-0000-000000000000", group_id: "00000000-0000-0000-0000-000000000000") 
}
```

### update_product_stock
```graphql
mutation {
  update_product_stock(product_id: "00000000-0000-0000-0000-000000000000", stock: "") {
    id
    tenant_id
    product_id
  }
}
```

### create_category
```graphql
mutation {
  create_category(input: { title: "", parent_id: "00000000-0000-0000-0000-000000000000", subtitle: [""], description: [""], description_long: [""], sku: [""], thumbnail_media_id: "00000000-0000-0000-0000-000000000000", media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### update_category
```graphql
mutation {
  update_category(id: "00000000-0000-0000-0000-000000000000", input: { title: [""], parent_id: "00000000-0000-0000-0000-000000000000", subtitle: [""], description: [""], description_long: [""], sku: [""], thumbnail_media_id: "00000000-0000-0000-0000-000000000000", media: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" } }) {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### delete_category
```graphql
mutation {
  delete_category(id: "00000000-0000-0000-0000-000000000000") 
}
```

### set_product_categories
```graphql
mutation {
  set_product_categories(product_id: "00000000-0000-0000-0000-000000000000", category_ids: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    parent_id
    thumbnail_media_id
  }
}
```

### create_pricing_type
```graphql
mutation {
  create_pricing_type(input: { type: "" }) {
    id
    tenant_id
  }
}
```

### update_pricing_type
```graphql
mutation {
  update_pricing_type(id: "00000000-0000-0000-0000-000000000000", input: { type: "" }) {
    id
    tenant_id
  }
}
```

### delete_pricing_type
```graphql
mutation {
  delete_pricing_type(id: "00000000-0000-0000-0000-000000000000") 
}
```

### set_product_price
```graphql
mutation {
  set_product_price(input: { product_id: "00000000-0000-0000-0000-000000000000", pricing_type_id: "00000000-0000-0000-0000-000000000000", price: "" }) {
    id
    product_id
    pricing_type_id
  }
}
```

### delete_product_price
```graphql
mutation {
  delete_product_price(product_id: "00000000-0000-0000-0000-000000000000", pricing_type_id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_product_pricing_rule
```graphql
mutation {
  create_product_pricing_rule(input: { product_id: "00000000-0000-0000-0000-000000000000", name: "", priority: "", rule_type: "", value: "", min_quantity: [""], max_quantity: [""], location_id: "00000000-0000-0000-0000-000000000000", pincode: [""], start_time: [""], end_time: [""], day_of_week: [""], start_hour: [""], end_hour: [""], min_stock: [""], max_stock: [""], pricing_type_id: "00000000-0000-0000-0000-000000000000" }) {
    id
    product_id
    location_id
    pricing_type_id
  }
}
```

### delete_product_pricing_rule
```graphql
mutation {
  delete_product_pricing_rule(id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_media
```graphql
mutation {
  create_media(input: { file_path: "", media_url: "", media_type: "", file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" }) {
    id
    tenant_id
    entity_id
    meta_attributes
  }
}
```

### update_media
```graphql
mutation {
  update_media(id: "00000000-0000-0000-0000-000000000000", input: { file_path: [""], media_url: [""], media_type: [""], file_extension: [""], alt_text: [""], meta_attributes: "{}", entity_name: [""], entity_id: "00000000-0000-0000-0000-000000000000" }) {
    id
    tenant_id
    entity_id
    meta_attributes
  }
}
```

### delete_media
```graphql
mutation {
  delete_media(id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_coupon
```graphql
mutation {
  create_coupon(input: { code: "", discount_type: "", discount_value: "", start_date: "", end_date: "", description: [""], min_order_value: "", max_discount_amount: [""], usage_limit_total: [""], usage_limit_per_user: "", rules: "{}" }) {
    id
    tenant_id
    rules
  }
}
```

### update_coupon_status
```graphql
mutation {
  update_coupon_status(id: "00000000-0000-0000-0000-000000000000", is_active: "") {
    id
    tenant_id
    rules
  }
}
```

### apply_coupon
```graphql
mutation {
  apply_coupon(code: "", order_id: "00000000-0000-0000-0000-000000000000") 
}
```

### select_delivery_option
```graphql
mutation {
  select_delivery_option(address_id: "00000000-0000-0000-0000-000000000000", service_name: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### checkout_cart
```graphql
mutation {
  checkout_cart(payment_method: "") {
    id
    user_id
    delivery_address_id
  }
}
```

### record_payment
```graphql
mutation {
  record_payment(order_id: "00000000-0000-0000-0000-000000000000", amount: "", payment_method: "", transaction_reference: [""], status: "") {
    id
    order_id
    gateway_response
  }
}
```

### request_order_return
```graphql
mutation {
  request_order_return(input: { order_id: "00000000-0000-0000-0000-000000000000", reason: "", items: { order_item_id: "00000000-0000-0000-0000-000000000000", quantity: "", condition: "" } }) {
    id
    order_id
  }
}
```

### approve_order_return
```graphql
mutation {
  approve_order_return(return_id: "00000000-0000-0000-0000-000000000000", approved: "") {
    id
    order_id
  }
}
```

### complete_order_return
```graphql
mutation {
  complete_order_return(return_id: "00000000-0000-0000-0000-000000000000", refund_amount: "") {
    id
    order_id
  }
}
```

### create_product_review
```graphql
mutation {
  create_product_review(input: { product_id: "00000000-0000-0000-0000-000000000000", rating_points: "", review: [""] }) {
    id
    user_id
    product_id
  }
}
```

### create_order_review
```graphql
mutation {
  create_order_review(input: { order_id: "00000000-0000-0000-0000-000000000000", rating_points: "", review: [""] }) {
    id
    user_id
    order_id
  }
}
```

### create_company_review
```graphql
mutation {
  create_company_review(input: { tenant_id: "00000000-0000-0000-0000-000000000000", rating_points: "", review: [""] }) {
    id
    user_id
    tenant_id
  }
}
```

### update_product_review_status
```graphql
mutation {
  update_product_review_status(id: "00000000-0000-0000-0000-000000000000", status: "") {
    id
    user_id
    product_id
  }
}
```

### update_order_review_status
```graphql
mutation {
  update_order_review_status(id: "00000000-0000-0000-0000-000000000000", status: "") {
    id
    user_id
    order_id
  }
}
```

### update_company_review_status
```graphql
mutation {
  update_company_review_status(id: "00000000-0000-0000-0000-000000000000", status: "") {
    id
    user_id
    tenant_id
  }
}
```

### credit_wallet
```graphql
mutation {
  credit_wallet(user_id: "00000000-0000-0000-0000-000000000000", points: "", remarks: [""]) {
    id
    user_id
    wallet_id
    payment_id
    order_id
  }
}
```

### debit_wallet
```graphql
mutation {
  debit_wallet(user_id: "00000000-0000-0000-0000-000000000000", points: "", remarks: [""]) {
    id
    user_id
    wallet_id
    payment_id
    order_id
  }
}
```

### generate_referral_code
```graphql
mutation {
  generate_referral_code(custom_code: [""]) {
    id
    user_id
  }
}
```

### claim_referral
```graphql
mutation {
  claim_referral(input: { referrer_code: "", referred_entity: "", referred_entity_id: "00000000-0000-0000-0000-000000000000", points: "", payment_id: "00000000-0000-0000-0000-000000000000", order_id: "00000000-0000-0000-0000-000000000000", remarks: [""] }) {
    id
    referral_user_id
    referrer_user_id
    referred_entity_id
  }
}
```

### configure_platform_gateway
```graphql
mutation {
  configure_platform_gateway(input: { name: "", credentials: "{}", webhook_secret: [""], is_active: "" }) {
    id
    credentials
  }
}
```

### activate_platform_gateway
```graphql
mutation {
  activate_platform_gateway(id: "00000000-0000-0000-0000-000000000000") {
    id
    credentials
  }
}
```

### configure_tenant_gateway
```graphql
mutation {
  configure_tenant_gateway(input: { gateway_id: "00000000-0000-0000-0000-000000000000", credentials: "{}", webhook_secret: [""], is_active: "" }) {
    id
    tenant_id
    gateway_id
    credentials
  }
}
```

### activate_tenant_gateway
```graphql
mutation {
  activate_tenant_gateway(id: "00000000-0000-0000-0000-000000000000") {
    id
    tenant_id
    gateway_id
    credentials
  }
}
```

### configure_tenant_commission
```graphql
mutation {
  configure_tenant_commission(input: { commission_percent: "", linked_account_id: "" }) {
    id
    tenant_id
  }
}
```

### initiate_online_payment
```graphql
mutation {
  initiate_online_payment(order_id: "00000000-0000-0000-0000-000000000000") 
}
```

### initiate_cart_payment
```graphql
mutation {
  initiate_cart_payment 
}
```

### create_subscription_plan
```graphql
mutation {
  create_subscription_plan(input: { title: "", price: "", billing_cycle: "", type: "", description: [""], is_active: [""] }) {
    id
  }
}
```

### update_subscription_plan
```graphql
mutation {
  update_subscription_plan(id: "00000000-0000-0000-0000-000000000000", input: { title: [""], price: [""], billing_cycle: [""], type: [""], description: [""], is_active: [""] }) {
    id
  }
}
```

### delete_subscription_plan
```graphql
mutation {
  delete_subscription_plan(id: "00000000-0000-0000-0000-000000000000") 
}
```

### create_subscription_features
```graphql
mutation {
  create_subscription_features(input: { plan_id: "00000000-0000-0000-0000-000000000000", user_limit: [""], product_limit: [""], coupon_limit: [""], cod_enabled: [""], cms_enabled: [""], otp_login_enabled: [""], custom_domain_enabled: [""] }) {
    id
    plan_id
  }
}
```

### update_subscription_features
```graphql
mutation {
  update_subscription_features(plan_id: "00000000-0000-0000-0000-000000000000", input: { user_limit: [""], product_limit: [""], coupon_limit: [""], cod_enabled: [""], cms_enabled: [""], otp_login_enabled: [""], custom_domain_enabled: [""] }) {
    id
    plan_id
  }
}
```

### subscribe_tenant
```graphql
mutation {
  subscribe_tenant(input: { plan_id: "00000000-0000-0000-0000-000000000000", start_date: "", end_date: "", status: [""], coupon_id: "00000000-0000-0000-0000-000000000000", remark: [""] }) {
    id
    tenant_id
    plan_id
    coupon_id
  }
}
```

### renew_tenant_subscription
```graphql
mutation {
  renew_tenant_subscription(input: { plan_id: "00000000-0000-0000-0000-000000000000", start_date: "", end_date: "", coupon_id: "00000000-0000-0000-0000-000000000000", remark: [""] }) {
    id
    tenant_id
    plan_id
    coupon_id
  }
}
```

### cancel_tenant_subscription
```graphql
mutation {
  cancel_tenant_subscription(remark: [""]) {
    id
    tenant_id
    plan_id
    coupon_id
  }
}
```

### create_tenant_subscription_payment
```graphql
mutation {
  create_tenant_subscription_payment(input: { tenant_subscription_id: "00000000-0000-0000-0000-000000000000", amount: "", payment_method: "", status: [""], transaction_id: [""], paid_at: [""] }) {
    id
    tenant_subscription_id
  }
}
```

### create_or_update_homepage_config
```graphql
mutation {
  create_or_update_homepage_config(input: { status: "", sections: { type: "", title: "", config: "{}", id: "00000000-0000-0000-0000-000000000000", order: "" } }) {
    tenant_id
  }
}
```

### update_homepage_config
```graphql
mutation {
  update_homepage_config(input: { status: [""], sections: { type: "", title: "", config: "{}", id: "00000000-0000-0000-0000-000000000000", order: "" } }) {
    tenant_id
  }
}
```

### delete_homepage_section
```graphql
mutation {
  delete_homepage_section(section_id: "00000000-0000-0000-0000-000000000000") 
}
```

