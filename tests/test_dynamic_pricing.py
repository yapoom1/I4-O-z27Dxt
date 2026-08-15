import asyncio
import uuid
import sys
import os
from datetime import datetime
from decimal import Decimal

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphql.schema import schema
from app.graphql.context import GraphQLContext
from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.database.redis import redis_client
from app.users.models import User
from app.orders.models import Order, OrderItem
from sqlalchemy.future import select

# Generate unique names for each test run to prevent unique constraint failures
rand_id = uuid.uuid4().hex[:6]
TEST_BUSINESS_NAME = f"PricingCorp {rand_id}"
TEST_ADMIN_EMAIL = f"admin_{rand_id}@pricingcorp.com"
TEST_ADMIN_MOBILE = f"987654{rand_id}"
TEST_ADMIN_PASSWORD = "Password123!"

class MockRequest:
    """Mock HTTP request to supply headers to get_graphql_context/resolvers."""
    def __init__(self, headers=None):
        self.headers = headers or {}

async def run_dynamic_pricing_test():
    print("=== STARTING DYNAMIC PRICING INTEGRATION TEST ===")
    
    # 1. Initialize databases
    print("Initializing Redis...")
    redis_client.connect()
    
    print("Initializing MongoDB...")
    try:
        mongo_client = await init_mongodb()
        print("MongoDB connected!")
    except Exception as e:
        print(f"Warning: MongoDB connection failed ({e}). Proceeding without Beanie ODM.")
        mongo_client = None

    # Initialize PostgreSQL tables if they don't exist
    print("Initializing PostgreSQL (running create_all)...")
    await init_postgres()

    # Open PostgreSQL session
    async with AsyncSessionLocal() as db:
        def make_context(user=None, tenant_id=None):
            return GraphQLContext(db=db, tenant_id=tenant_id, user=user)

        # 2. Setup Tenant & Admin
        print("\n--- Creating Tenant ---")
        create_tenant_mutation = """
            mutation CreateTenant($input: CreateTenantInput!) {
                createTenant(input: $input) {
                    id
                    businessName
                }
            }
        """
        variables = {
            "input": {
                "businessName": TEST_BUSINESS_NAME,
                "adminName": "Pricing Admin",
                "adminEmail": TEST_ADMIN_EMAIL,
                "adminMobile": TEST_ADMIN_MOBILE,
                "adminPassword": TEST_ADMIN_PASSWORD
            }
        }
        
        result = await schema.execute(
            create_tenant_mutation,
            variable_values=variables,
            context_value=make_context()
        )
        assert not result.errors, f"CreateTenant error: {result.errors}"
        tenant_id_str = result.data["createTenant"]["id"]
        tenant_id = uuid.UUID(tenant_id_str)
        print(f"Tenant created: {tenant_id_str}")

        # Fetch actual DB user model to simulate decoded context user
        stmt = select(User).where((User.tenant_id == tenant_id) & (User.email == TEST_ADMIN_EMAIL))
        res = await db.execute(stmt)
        db_user = res.scalar_one_or_none()
        assert db_user is not None, "Admin user should exist in DB"
        print(f"Admin User ID: {db_user.id}")

        # 3. Create Pricing Type (selling_price)
        print("\n--- Creating Pricing Type 'selling_price' ---")
        create_pt_mutation = """
            mutation CreatePricingType($input: CreatePricingTypeInput!) {
                createPricingType(input: $input) {
                    id
                    type
                }
            }
        """
        result = await schema.execute(
            create_pt_mutation,
            variable_values={"input": {"type": "selling_price"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"CreatePricingType error: {result.errors}"
        pt_selling_id_str = result.data["createPricingType"]["id"]
        print(f"Pricing Type created: {pt_selling_id_str}")

        # 4. Create Product
        print("\n--- Creating Product ---")
        create_product_mutation = """
            mutation CreateProduct($input: CreateProductInput!) {
                createProduct(input: $input) {
                    id
                    title
                    sku
                }
            }
        """
        variables_prod = {
            "input": {
                "title": "Premium Widget",
                "productType": "GOODS",
                "sku": f"WIDGET-{rand_id}",
            }
        }
        result = await schema.execute(
            create_product_mutation,
            variable_values=variables_prod,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"CreateProduct error: {result.errors}"
        product_id_str = result.data["createProduct"]["id"]
        print(f"Product created: {product_id_str}")

        # 5. Set Base Price (selling_price = 100.00)
        print("\n--- Setting Product Base Price to 100.00 ---")
        set_price_mutation = """
            mutation SetProductPrice($input: SetProductPriceInput!) {
                setProductPrice(input: $input) {
                    price
                }
            }
        """
        result = await schema.execute(
            set_price_mutation,
            variable_values={
                "input": {
                    "productId": product_id_str,
                    "pricingTypeId": pt_selling_id_str,
                    "price": 100.00
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"SetProductPrice error: {result.errors}"
        print("Base price set successfully.")

        # 6. Set Stock Level (stock = 10)
        print("\n--- Setting Product Stock level to 10 ---")
        set_stock_mutation = """
            mutation UpdateProductStock($productId: UUID!, $stock: Int!) {
                updateProductStock(productId: $productId, stock: $stock) {
                    stock
                }
            }
        """
        result = await schema.execute(
            set_stock_mutation,
            variable_values={
                "productId": product_id_str,
                "stock": 10
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"UpdateProductStock error: {result.errors}"
        print("Stock level set to 10.")

        # 7. Create Addresses (one matching target pincode, one other)
        print("\n--- Creating User Addresses ---")
        create_address_mutation = """
            mutation CreateUserAddress($input: CreateUserAddressInput!) {
                createUserAddress(input: $input) {
                    id
                    pincode
                }
            }
        """
        # Address 1: Target pincode "560001"
        result1 = await schema.execute(
            create_address_mutation,
            variable_values={
                "input": {
                    "addressLine1": "Pincode St 1",
                    "pincode": "560001",
                    "state": "StateOne",
                    "district": "DistrictOne",
                    "customerName": "John Pincode",
                    "phoneNumber": "9998887771",
                    "isPrimary": True
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result1.errors, f"CreateUserAddress 1 error: {result1.errors}"
        addr_target_id = result1.data["createUserAddress"]["id"]

        # Address 2: Other pincode "560002"
        result2 = await schema.execute(
            create_address_mutation,
            variable_values={
                "input": {
                    "addressLine1": "Pincode St 2",
                    "pincode": "560002",
                    "state": "StateOne",
                    "district": "DistrictOne",
                    "customerName": "Jane Other",
                    "phoneNumber": "9998887772",
                    "isPrimary": False
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result2.errors, f"CreateUserAddress 2 error: {result2.errors}"
        addr_other_id = result2.data["createUserAddress"]["id"]

        # Query cart query structure
        query_cart = """
            query {
                myCart {
                    id
                    deliveryAddressId
                    items {
                        id
                        productId
                        quantity
                    }
                    billSummary {
                        itemTotal
                        grandTotal
                    }
                }
            }
        """

        add_to_cart_mutation = """
            mutation AddToCart($productId: UUID!, $quantity: Int!) {
                addToCart(productId: $productId, quantity: $quantity) {
                    id
                }
            }
        """

        select_delivery_mutation = """
            mutation SelectDelivery($addressId: UUID!, $serviceName: String!) {
                selectDeliveryOption(addressId: $addressId, serviceName: $serviceName) {
                    deliveryAddressId
                }
            }
        """

        # Populate Cart with 1 unit
        print("\n--- Adding 1 unit of product to Cart ---")
        result = await schema.execute(
            add_to_cart_mutation,
            variable_values={
                "productId": product_id_str,
                "quantity": 1
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"AddToCart error: {result.errors}"

        # Check cart with NO rules yet
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert not result.errors
        cart_data = result.data["myCart"]
        assert cart_data["billSummary"]["itemTotal"] == 100.00, f"Expected 100.00, got {cart_data['billSummary']['itemTotal']}"
        print("Cart item total without rules is correctly 100.00")

        # 8. Create Pricing Rules Mutation
        create_rule_mutation = """
            mutation CreateProductPricingRule($input: CreateProductPricingRuleInput!) {
                createProductPricingRule(input: $input) {
                    id
                    name
                    priority
                    ruleType
                    value
                }
            }
        """

        print("\n--- TEST SCENARIO 1: Quantity Volume Tier Rule ---")
        # Rule: Min quantity = 5 -> 20% DISCOUNT (priority = 10)
        result = await schema.execute(
            create_rule_mutation,
            variable_values={
                "input": {
                    "productId": product_id_str,
                    "name": "Volume Discount",
                    "priority": 10,
                    "ruleType": "DISCOUNT_PERCENT",
                    "value": 20.0,
                    "minQuantity": 5
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"CreateProductPricingRule error: {result.errors}"
        rule_qty_id = result.data["createProductPricingRule"]["id"]
        print(f"Created Quantity Rule: {rule_qty_id}")

        # Check cart itemTotal with quantity 1 (should NOT apply)
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 100.00
        print("Quantity rule correctly not applied for qty = 1")

        # Set quantity to 5
        print("Updating cart quantity to 5...")
        result = await schema.execute(
            add_to_cart_mutation,
            variable_values={
                "productId": product_id_str,
                "quantity": 4  # increment by 4 to make it 5
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        
        # Check cart itemTotal (should apply: 5 * (100 - 20%) = 5 * 80 = 400)
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert not result.errors
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 400.00, f"Expected 400.00, got {result.data['myCart']['billSummary']['itemTotal']}"
        print("Quantity rule successfully applied: qty 5 total = 400.00 (80.00 each)")

        print("\n--- TEST SCENARIO 2: Location/Pincode Rule ---")
        # Rule: Pincode "560001" -> 15.00 DISCOUNT_FIXED (priority = 20)
        # Note: Priority is higher than volume discount, so it overrides it if both apply!
        result = await schema.execute(
            create_rule_mutation,
            variable_values={
                "input": {
                    "productId": product_id_str,
                    "name": "Local Discount",
                    "priority": 20,
                    "ruleType": "DISCOUNT_FIXED",
                    "value": 15.0,
                    "pincode": "560001"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        rule_loc_id = result.data["createProductPricingRule"]["id"]
        print(f"Created Pincode Rule: {rule_loc_id}")

        # Set Cart Address to Other Pincode "560002"
        print("Setting cart address to other pincode (560002)...")
        result = await schema.execute(
            select_delivery_mutation,
            variable_values={"addressId": addr_other_id, "serviceName": "Standard"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors

        # Check cart total. Pincode rule does NOT apply, so Quantity rule (priority 10) still applies.
        # Total should be 400.00.
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 400.00
        print("Other pincode address correctly keeps volume discount")

        # Set Cart Address to Target Pincode "560001"
        print("Setting cart address to target pincode (560001)...")
        result = await schema.execute(
            select_delivery_mutation,
            variable_values={"addressId": addr_target_id, "serviceName": "Standard"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors

        # Check cart total. Pincode rule (priority 20) applies!
        # Dynamic price: 100 - 15 = 85.00.
        # Total should be 5 * 85 = 425.00.
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 425.00, f"Expected 425.00, got {result.data['myCart']['billSummary']['itemTotal']}"
        print("Local address discount correctly applied and overrides quantity rule: qty 5 total = 425.00 (85.00 each)")

        print("\n--- TEST SCENARIO 3: Happy Hour recurring Time Rule ---")
        # Rule: start_hour and end_hour enclosing current hour -> 10.00 MARKUP_FIXED (priority = 30)
        current_hour = datetime.utcnow().hour
        start_hour = current_hour
        end_hour = (current_hour + 1) % 24

        result = await schema.execute(
            create_rule_mutation,
            variable_values={
                "input": {
                    "productId": product_id_str,
                    "name": "Rush Hour Markup",
                    "priority": 30,
                    "ruleType": "MARKUP_FIXED",
                    "value": 10.0,
                    "startHour": start_hour,
                    "endHour": end_hour
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        rule_time_id = result.data["createProductPricingRule"]["id"]
        print(f"Created Happy Hour Rule: {rule_time_id} (Hours: {start_hour} - {end_hour})")

        # Check cart total. Time rule (priority 30) applies!
        # Dynamic price: 100 + 10 = 110.00.
        # Total: 5 * 110 = 550.00.
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 550.00, f"Expected 550.00, got {result.data['myCart']['billSummary']['itemTotal']}"
        print("Happy hour markup correctly applied: qty 5 total = 550.00 (110.00 each)")

        print("\n--- TEST SCENARIO 4: Low Stock Rule ---")
        # Rule: max_stock = 5 -> 50% MARKUP_PERCENT (priority = 40)
        result = await schema.execute(
            create_rule_mutation,
            variable_values={
                "input": {
                    "productId": product_id_str,
                    "name": "Scarcity Pricing",
                    "priority": 40,
                    "ruleType": "MARKUP_PERCENT",
                    "value": 50.0,
                    "maxStock": 5
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        rule_stock_id = result.data["createProductPricingRule"]["id"]
        print(f"Created Low Stock Rule: {rule_stock_id}")

        # Currently stock is 10. Rule should not apply. Total remains 550.00 (from priority 30 rule).
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 550.00
        print("Low stock rule correctly skipped when stock is high (10)")

        # Change stock to 3
        print("Setting stock to 3...")
        result = await schema.execute(
            set_stock_mutation,
            variable_values={
                "productId": product_id_str,
                "stock": 3
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors

        # Check cart total. Low stock rule (priority 40) applies!
        # Dynamic price: 100 + 50% = 150.00.
        # Total: 5 * 150 = 750.00.
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 750.00, f"Expected 750.00, got {result.data['myCart']['billSummary']['itemTotal']}"
        print("Low stock markup correctly applied: qty 5 total = 750.00 (150.00 each)")

        print("\n--- TEST SCENARIO 5: Rule Deletion & Priority Rollback ---")
        # Delete the Low Stock rule
        print("Deleting Low Stock rule...")
        delete_rule_mutation = """
            mutation DeleteProductPricingRule($id: UUID!) {
                deleteProductPricingRule(id: $id)
            }
        """
        result = await schema.execute(
            delete_rule_mutation,
            variable_values={"id": rule_stock_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["deleteProductPricingRule"] is True

        # Total should roll back to Time Rule (550.00)
        result = await schema.execute(query_cart, context_value=make_context(user=db_user, tenant_id=tenant_id))
        assert result.data["myCart"]["billSummary"]["itemTotal"] == 550.00, f"Expected 550.00, got {result.data['myCart']['billSummary']['itemTotal']}"
        print("After deleting low stock rule, price correctly rolled back to time rule (550.00)")

        print("\n--- TEST SCENARIO 6: Checkout Order Unit Price Integration ---")
        # Run checkout Cart
        checkout_mutation = """
            mutation CheckoutCart($paymentMethod: String!) {
                checkoutCart(paymentMethod: $paymentMethod) {
                    id
                    itemTotal
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
        """
        result = await schema.execute(
            checkout_mutation,
            variable_values={"paymentMethod": "CASH"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"Checkout error: {result.errors}"
        order_data = result.data["checkoutCart"]
        assert order_data["itemTotal"] == 550.00, f"Expected order itemTotal 550.00, got {order_data['itemTotal']}"
        order_item = order_data["items"][0]
        assert order_item["unitPrice"] == 110.00, f"Expected OrderItem unitPrice 110.00, got {order_item['unitPrice']}"
        assert order_item["subtotal"] == 550.00, f"Expected OrderItem subtotal 550.00, got {order_item['subtotal']}"
        print("Order successfully created with correct dynamic price (110.00 unitPrice, 550.00 total)!")

        print("\n--- TEST SCENARIO 7: Scoped Pricing Rules & Attribute-Based Pricing Types ---")
        # 1. Create Pricing Type 'cost'
        res_pt_cost = await schema.execute(
            create_pt_mutation,
            variable_values={"input": {"type": "cost"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not res_pt_cost.errors, f"Cost pricing type creation errors: {res_pt_cost.errors}"
        cost_price_type_id = res_pt_cost.data["createPricingType"]["id"]
        print("Cost pricing type created successfully.")

        # 2. Set base price for 'cost' to 60.00
        set_price_mutation = """
            mutation SetProductPrice($input: SetProductPriceInput!) {
                setProductPrice(input: $input) {
                    id
                    price
                }
            }
        """
        await schema.execute(
            set_price_mutation,
            variable_values={"input": {"productId": product_id_str, "pricingTypeId": cost_price_type_id, "price": 60.00}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        print("Base cost price set successfully to 60.00.")

        # 3. Query effective price for 'cost' explicitly
        query_effective_price = """
            query GetEffectivePrice($id: UUID!, $pricingType: String) {
                product(id: $id) {
                    effectivePrice(pricingType: $pricingType)
                }
            }
        """
        res_eff_cost = await schema.execute(
            query_effective_price,
            variable_values={"id": product_id_str, "pricingType": "cost"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_eff_cost.data["product"]["effectivePrice"] == 60.00, f"Expected 60.00, got {res_eff_cost.data['product']['effectivePrice']}"
        print("Explicit cost price resolved successfully to 60.00.")

        # 4. Create dynamic pricing rule targeting 'cost'
        create_rule_mutation_with_type = """
            mutation CreateProductPricingRule($input: CreateProductPricingRuleInput!) {
                createProductPricingRule(input: $input) {
                    id
                    pricingTypeId
                }
            }
        """
        res_rule_cost = await schema.execute(
            create_rule_mutation_with_type,
            variable_values={"input": {
                "productId": product_id_str,
                "name": "Cost Markup Rule",
                "priority": 100,
                "ruleType": "MARKUP_FIXED",
                "value": 15.00,
                "pricingTypeId": cost_price_type_id
            }},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not res_rule_cost.errors, f"Rule creation errors: {res_rule_cost.errors}"
        rule_cost_id = res_rule_cost.data["createProductPricingRule"]["id"]
        print("Pricing rule scoped to 'cost' created successfully.")

        # 5. Query effective price for 'cost' and verify it applies the markup (60.00 + 15.00 = 75.00)
        res_eff_cost_marked = await schema.execute(
            query_effective_price,
            variable_values={"id": product_id_str, "pricingType": "cost"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_eff_cost_marked.data["product"]["effectivePrice"] == 75.00, f"Expected 75.00, got {res_eff_cost_marked.data['product']['effectivePrice']}"
        print("Explicit cost price dynamic markup applied successfully: 75.00.")

        # 6. Query effective price for 'selling_price' and verify it does NOT apply the cost rule
        res_eff_selling = await schema.execute(
            query_effective_price,
            variable_values={"id": product_id_str, "pricingType": "selling_price"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_eff_selling.data["product"]["effectivePrice"] != 75.00, "Selling price should not match cost rules"
        print("Selling price successfully isolated from cost rules.")

        # 7. Create attribute 'membership' and value 'wholesale'
        create_attr_mutation = """
            mutation CreateAttribute($input: CreateAttributeInput!) {
                createAttribute(input: $input) {
                    id
                }
            }
        """
        res_attr = await schema.execute(
            create_attr_mutation,
            variable_values={"input": {"name": "membership", "displayName": "Membership Tier"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        attr_id = res_attr.data["createAttribute"]["id"]

        create_val_mutation = """
            mutation CreateAttributeValue($input: CreateAttributeValueInput!) {
                createAttributeValue(input: $input) {
                    id
                }
            }
        """
        res_val = await schema.execute(
            create_val_mutation,
            variable_values={"input": {"attributeId": attr_id, "value": "wholesale"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        val_id = res_val.data["createAttributeValue"]["id"]
        print("Membership attribute and wholesale value created.")

        # 8. Assign attribute to product with pricing_type_id override set to 'cost'
        assign_attr_mutation = """
            mutation AssignAttributeValueToProduct($productId: UUID!, $attributeValueId: UUID!, $pricingTypeId: UUID) {
                assignAttributeValueToProduct(productId: $productId, attributeValueId: $attributeValueId, pricingTypeId: $pricingTypeId) {
                    id
                    pricingTypeId
                }
            }
        """
        res_assign = await schema.execute(
            assign_attr_mutation,
            variable_values={"productId": product_id_str, "attributeValueId": val_id, "pricingTypeId": cost_price_type_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_assign.data["assignAttributeValueToProduct"]["pricingTypeId"] == cost_price_type_id
        print("Attribute value assigned to product with cost override mapping.")

        # 9. Query effective price WITHOUT specifying pricing type. It should override default (selling_price) to cost (75.00)
        res_eff_default = await schema.execute(
            query_effective_price,
            variable_values={"id": product_id_str},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_eff_default.data["product"]["effectivePrice"] == 75.00, f"Expected 75.00 override, got {res_eff_default.data['product']['effectivePrice']}"
        print("Pricing type correctly overridden dynamically based on ProductAttributeValue: 75.00.")

        # 10. Explicitly query selling_price and verify it overrides the attribute fallback
        res_eff_selling_explicit = await schema.execute(
            query_effective_price,
            variable_values={"id": product_id_str, "pricingType": "selling_price"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert res_eff_selling_explicit.data["product"]["effectivePrice"] != 75.00
        print("Explicit pricingType parameter successfully overrides the attribute value mapping override.")

        # Clean up Scenario 7 objects
        await schema.execute(delete_rule_mutation, variable_values={"id": rule_cost_id}, context_value=make_context(user=db_user, tenant_id=tenant_id))
        from sqlalchemy import delete
        from app.products.products.models import ProductAttributeValue, AttributeValue, Attribute
        await db.execute(delete(ProductAttributeValue))
        await db.execute(delete(AttributeValue))
        await db.execute(delete(Attribute))
        await db.commit()

        # 9. Clean up rules & product
        print("\n--- Cleaning up ---")
        # Delete rules
        await schema.execute(delete_rule_mutation, variable_values={"id": rule_qty_id}, context_value=make_context(user=db_user, tenant_id=tenant_id))
        await schema.execute(delete_rule_mutation, variable_values={"id": rule_loc_id}, context_value=make_context(user=db_user, tenant_id=tenant_id))
        await schema.execute(delete_rule_mutation, variable_values={"id": rule_time_id}, context_value=make_context(user=db_user, tenant_id=tenant_id))
        
        # Delete orders and order items first to satisfy foreign key constraints
        stmt_order = select(Order).where(Order.tenant_id == tenant_id)
        res_order = await db.execute(stmt_order)
        orders = res_order.scalars().all()
        for o in orders:
            stmt_oi = select(OrderItem).where(OrderItem.order_id == o.id)
            res_oi = await db.execute(stmt_oi)
            ois = res_oi.scalars().all()
            for oi in ois:
                await db.delete(oi)
            await db.delete(o)
        await db.flush()

        # Delete product
        delete_product_mutation = """
            mutation DeleteProduct($id: UUID!) {
                deleteProduct(id: $id)
            }
        """
        await schema.execute(
            delete_product_mutation,
            variable_values={"id": product_id_str},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        print("Cleaned up rules and products successfully.")

    # Close DB connection
    await redis_client.close()
    if mongo_client:
        mongo_client.close()
        
    print("\n=== DYNAMIC PRICING INTEGRATION TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_dynamic_pricing_test())
