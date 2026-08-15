import asyncio
import uuid
import sys
import os

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphql.schema import schema
from app.graphql.context import GraphQLContext
from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.database.redis import redis_client
from app.users.models import User
from app.tenants.models import Tenant
from sqlalchemy.future import select

# Generate unique names for each test run to prevent unique constraint failures
rand_id = uuid.uuid4().hex[:6]
TEST_BUSINESS_NAME = f"DreamCorp {rand_id}"
TEST_ADMIN_EMAIL = f"admin_{rand_id}@dreamcorp.com"
TEST_ADMIN_MOBILE = f"998877{rand_id}"
TEST_ADMIN_PASSWORD = "SuperSecretPassword123"

class MockRequest:
    """Mock HTTP request to supply headers to get_graphql_context/resolvers."""
    def __init__(self, headers=None):
        self.headers = headers or {}


async def run_integration_test():
    print("=== STARTING INTEGRATION TEST ===")
    
    # 1. Initialize databases
    print("Initializing Redis...")
    redis_client.connect()
    
    print("Initializing MongoDB...")
    try:
        mongo_client = await init_mongodb()
        print("MongoDB/Beanie connected!")
    except Exception as e:
        print(f"Warning: MongoDB connection failed ({e}). Proceeding without Beanie ODM.")
        mongo_client = None

    # Initialize PostgreSQL tables if they don't exist
    print("Initializing PostgreSQL (running create_all)...")
    await init_postgres()

    # Open PostgreSQL session
    async with AsyncSessionLocal() as db:
        # Define context helper
        def make_context(user=None, tenant_id=None):
            return GraphQLContext(db=db, tenant_id=tenant_id, user=user)

        # 2. Test Tenant & Admin Registration
        print("\n--- Test Mutation: createTenant ---")
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
                "adminName": "John Doe",
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
        
        if result.errors:
            print(f"CreateTenant Error: {result.errors}")
            return
            
        tenant_data = result.data["createTenant"]
        tenant_id_str = tenant_data["id"]
        print(f"Tenant successfully created: {tenant_data['businessName']} (ID: {tenant_id_str})")
        tenant_id = uuid.UUID(tenant_id_str)

        # 3. Test Password Login
        print("\n--- Test Mutation: loginWithPassword ---")
        login_pwd_mutation = """
            mutation LoginWithPassword($emailOrMobile: String!, $password: String!) {
                loginWithPassword(emailOrMobile: $emailOrMobile, password: $password) {
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
        """
        login_variables = {
            "emailOrMobile": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        }
        
        result = await schema.execute(
            login_pwd_mutation,
            variable_values=login_variables,
            context_value=make_context(tenant_id=tenant_id)
        )
        
        if result.errors:
            print(f"LoginWithPassword Error: {result.errors}")
            return
            
        auth_data = result.data["loginWithPassword"]
        access_token = auth_data["tokens"]["accessToken"]
        refresh_token = auth_data["tokens"]["refreshToken"]
        user_data = auth_data["user"]
        print(f"Login successful for user: {user_data['name']} (Role: {user_data['role']})")
        print(f"Tokens generated. Access Token starts with: {access_token[:20]}...")

        # 4. Test Send OTP Mutation
        print("\n--- Test Mutation: sendOtp ---")
        send_otp_mutation = """
            mutation SendOtp($mobilenumber: String!) {
                sendOtp(mobilenumber: $mobilenumber) {
                    success
                    message
                    otp
                }
            }
        """
        result = await schema.execute(
            send_otp_mutation,
            variable_values={"mobilenumber": TEST_ADMIN_MOBILE},
            context_value=make_context(tenant_id=tenant_id)
        )
        
        if result.errors:
            print(f"SendOtp Error: {result.errors}")
            return
            
        otp_data = result.data["sendOtp"]
        otp_code = otp_data["otp"]
        print(f"OTP Generation Result: {otp_data['message']} | Generated OTP code: {otp_code}")

        # 5. Test Login with OTP
        print("\n--- Test Mutation: loginWithOtp ---")
        login_otp_mutation = """
            mutation LoginWithOtp($mobilenumber: String!, $otp: String!) {
                loginWithOtp(mobilenumber: $mobilenumber, otp: $otp) {
                    tokens {
                        accessToken
                    }
                    user {
                        name
                        email
                    }
                }
            }
        """
        result = await schema.execute(
            login_otp_mutation,
            variable_values={"mobilenumber": TEST_ADMIN_MOBILE, "otp": otp_code},
            context_value=make_context(tenant_id=tenant_id)
        )
        
        if result.errors:
            print(f"LoginWithOtp Error: {result.errors}")
            return
            
        otp_login_data = result.data["loginWithOtp"]
        print(f"OTP login successful! User: {otp_login_data['user']['name']}")

        # 6. Test Query me (Authorized)
        print("\n--- Test Query: me (Authenticated) ---")
        query_me = """
            query {
                me {
                    id
                    name
                    email
                    mobilenumber
                    role
                    status
                    tenant {
                        businessName
                    }
                }
            }
        """
        # Fetch actual DB user model to simulate decoded context user
        stmt = select(User).where(User.id == uuid.UUID(user_data["id"]))
        res = await db.execute(stmt)
        db_user = res.scalar_one()

        result = await schema.execute(
            query_me,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        
        if result.errors:
            print(f"Query me Error: {result.errors}")
            return
            
        profile = result.data["me"]
        print(f"Fetched Profile Successfully: Name: {profile['name']} | Tenant: {profile['tenant']['businessName']}")

        # 6a. Test Mutation: createUserAddress (Primary Address)
        print("\n--- Test Mutation: createUserAddress (Primary) ---")
        create_address_mutation = """
            mutation CreateUserAddress($input: CreateUserAddressInput!) {
                createUserAddress(input: $input) {
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
        """
        variables_addr1 = {
            "input": {
                "addressLine1": "123 Main St",
                "addressLine2": "Suite 400",
                "landmark": "Near Clock Tower",
                "pincode": "123456",
                "state": "StateOne",
                "district": "DistrictOne",
                "customerName": "John Doe",
                "phoneNumber": "9988776655",
                "isPrimary": True,
                "latLong": "12.34,56.78",
                "thirdPartyAppAddress": "JSON block or text"
            }
        }
        result = await schema.execute(
            create_address_mutation,
            variable_values=variables_addr1,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateUserAddress 1 Error: {result.errors}")
            return
        addr1 = result.data["createUserAddress"]
        print(f"Address 1 Created: ID={addr1['id']}, addressLine1={addr1['addressLine1']}, isPrimary={addr1['isPrimary']}")
        assert addr1["isPrimary"] is True, "Address 1 should be primary"

        # 6b. Test Mutation: createUserAddress (Secondary Address)
        print("\n--- Test Mutation: createUserAddress (Secondary) ---")
        variables_addr2 = {
            "input": {
                "addressLine1": "456 Side St",
                "pincode": "654321",
                "state": "StateTwo",
                "district": "DistrictTwo",
                "customerName": "Jane Doe",
                "phoneNumber": "9988776644",
                "isPrimary": False
            }
        }
        result = await schema.execute(
            create_address_mutation,
            variable_values=variables_addr2,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateUserAddress 2 Error: {result.errors}")
            return
        addr2 = result.data["createUserAddress"]
        print(f"Address 2 Created: ID={addr2['id']}, addressLine1={addr2['addressLine1']}, isPrimary={addr2['isPrimary']}")
        assert addr2["isPrimary"] is False, "Address 2 should be secondary"

        # 6c. Test Query: my_addresses
        print("\n--- Test Query: myAddresses ---")
        query_addresses = """
            query {
                myAddresses {
                    id
                    addressLine1
                    isPrimary
                }
            }
        """
        result = await schema.execute(
            query_addresses,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query MyAddresses Error: {result.errors}")
            return
        addresses = result.data["myAddresses"]
        print(f"Fetched {len(addresses)} addresses.")
        assert len(addresses) == 2, "Expected 2 addresses"

        # 6d. Test Query: me resolving addresses
        print("\n--- Test Query: me with addresses ---")
        query_me_with_addresses = """
            query {
                me {
                    id
                    addresses {
                        id
                        addressLine1
                        isPrimary
                    }
                }
            }
        """
        result = await schema.execute(
            query_me_with_addresses,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query me with addresses Error: {result.errors}")
            return
        me_data = result.data["me"]
        print(f"Fetched user addresses relation: count={len(me_data['addresses'])}")
        assert len(me_data["addresses"]) == 2, "Expected 2 addresses via relationship"

        # 6e. Test Query: address(id)
        print("\n--- Test Query: address(id) ---")
        query_single_address = """
            query GetAddress($id: UUID!) {
                address(id: $id) {
                    id
                    addressLine1
                }
            }
        """
        result = await schema.execute(
            query_single_address,
            variable_values={"id": addr1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query single address Error: {result.errors}")
            return
        single_addr = result.data["address"]
        print(f"Single address fetched: ID={single_addr['id']}, line1={single_addr['addressLine1']}")
        assert single_addr["id"] == addr1["id"], "Fetched address ID mismatch"

        # 6f. Test Mutation: createUserAddress (Another Primary, overrides previous)
        print("\n--- Test Mutation: createUserAddress (Another Primary overrides previous) ---")
        variables_addr3 = {
            "input": {
                "addressLine1": "789 Third St",
                "pincode": "789123",
                "state": "StateThree",
                "district": "DistrictThree",
                "customerName": "Bob Smith",
                "phoneNumber": "9988776633",
                "isPrimary": True
            }
        }
        result = await schema.execute(
            create_address_mutation,
            variable_values=variables_addr3,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateUserAddress 3 Error: {result.errors}")
            return
        addr3 = result.data["createUserAddress"]
        print(f"Address 3 Created: ID={addr3['id']}, addressLine1={addr3['addressLine1']}, isPrimary={addr3['isPrimary']}")
        assert addr3["isPrimary"] is True, "Address 3 should be primary"

        # Refresh address 1 and verify it is no longer primary
        result = await schema.execute(
            query_addresses,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        addresses_refreshed = result.data["myAddresses"]
        addr1_refreshed = next(a for a in addresses_refreshed if a["id"] == addr1["id"])
        print(f"Address 1 refreshed isPrimary={addr1_refreshed['isPrimary']}")
        assert addr1_refreshed["isPrimary"] is False, "Address 1 should now be secondary"

        # 6g. Test Mutation: update_user_address (Toggle primary)
        print("\n--- Test Mutation: updateUserAddress (Make Address 2 Primary) ---")
        update_address_mutation = """
            mutation UpdateUserAddress($id: UUID!, $input: UpdateUserAddressInput!) {
                updateUserAddress(id: $id, input: $input) {
                    id
                    addressLine1
                    isPrimary
                }
            }
        """
        result = await schema.execute(
            update_address_mutation,
            variable_values={
                "id": addr2["id"],
                "input": {
                    "isPrimary": True
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateUserAddress Error: {result.errors}")
            return
        addr2_updated = result.data["updateUserAddress"]
        print(f"Address 2 updated: ID={addr2_updated['id']}, isPrimary={addr2_updated['isPrimary']}")
        assert addr2_updated["isPrimary"] is True, "Address 2 should now be primary"

        # Verify address 3 is no longer primary
        result = await schema.execute(
            query_addresses,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        addresses_refreshed2 = result.data["myAddresses"]
        addr3_refreshed = next(a for a in addresses_refreshed2 if a["id"] == addr3["id"])
        print(f"Address 3 refreshed isPrimary={addr3_refreshed['isPrimary']}")
        assert addr3_refreshed["isPrimary"] is False, "Address 3 should now be secondary"

        # 6h. Test Mutation: delete_user_address
        print("\n--- Test Mutation: deleteUserAddress (Delete Address 1) ---")
        delete_address_mutation = """
            mutation DeleteUserAddress($id: UUID!) {
                deleteUserAddress(id: $id)
            }
        """
        result = await schema.execute(
            delete_address_mutation,
            variable_values={"id": addr1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"DeleteUserAddress Error: {result.errors}")
            return
        deleted = result.data["deleteUserAddress"]
        print(f"Address 1 deleted: {deleted}")
        assert deleted is True, "Delete mutation should return true"

        # Verify Address 1 is gone
        result = await schema.execute(
            query_addresses,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        addresses_after_delete = result.data["myAddresses"]
        print(f"Remaining addresses: {len(addresses_after_delete)}")
        assert len(addresses_after_delete) == 2, "Should have 2 addresses remaining (addr2, addr3)"
        assert not any(a["id"] == addr1["id"] for a in addresses_after_delete), "Address 1 should not be in list"

        # 6i. Test Mutation: createProduct (Parent Product)
        print("\n--- Test Mutation: createProduct (Parent) ---")
        create_product_mutation = """
            mutation CreateProduct($input: CreateProductInput!) {
                createProduct(input: $input) {
                    id
                    title
                    subtitle
                    description
                    descriptionLong
                    sku
                    productType
                    thumbnailMediaId
                    parentId
                }
            }
        """
        variables_prod1 = {
            "input": {
                "title": "Professional E-Commerce Laptop",
                "productType": "GOODS",
                "subtitle": "High-end developer laptop",
                "description": "Powerful laptop with 32GB RAM",
                "descriptionLong": "Detailed specifications including 1TB SSD, 32GB RAM, and 8-Core CPU.",
                "sku": f"PROD-LAPTOP-{rand_id}",
                "thumbnailMediaId": "11111111-1111-1111-1111-111111111111"
            }
        }
        result = await schema.execute(
            create_product_mutation,
            variable_values=variables_prod1,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateProduct 1 Error: {result.errors}")
            return
        prod1 = result.data["createProduct"]
        print(f"Product 1 Created: ID={prod1['id']}, title={prod1['title']}, sku={prod1['sku']}")
        assert prod1["productType"] == "GOODS", "Product type should be GOODS"

        # 6j. Test Mutation: createProduct (Child Product / Variant)
        print("\n--- Test Mutation: createProduct (Child / Variant) ---")
        variables_prod2 = {
            "input": {
                "title": "Laptop 64GB Variant",
                "productType": "GOODS",
                "sku": f"PROD-LAPTOP-64G-{rand_id}",
                "parentId": prod1["id"]
            }
        }
        result = await schema.execute(
            create_product_mutation,
            variable_values=variables_prod2,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateProduct 2 Error: {result.errors}")
            return
        prod2 = result.data["createProduct"]
        print(f"Product 2 Created: ID={prod2['id']}, parentId={prod2['parentId']}")
        assert prod2["parentId"] == prod1["id"], "Parent ID should match Product 1"

        # 6ja. Test Mutation: createPricingType (selling_price)
        print("\n--- Test Mutation: createPricingType (selling_price) ---")
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
        if result.errors:
            print(f"CreatePricingType selling_price Error: {result.errors}")
            return
        pt_selling = result.data["createPricingType"]
        print(f"Pricing Type 'selling_price' Created: ID={pt_selling['id']}")
        assert pt_selling["type"] == "selling_price"

        # 6jb. Test Mutation: createPricingType (cost)
        print("\n--- Test Mutation: createPricingType (cost) ---")
        result = await schema.execute(
            create_pt_mutation,
            variable_values={"input": {"type": "cost"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreatePricingType cost Error: {result.errors}")
            return
        pt_cost = result.data["createPricingType"]
        print(f"Pricing Type 'cost' Created: ID={pt_cost['id']}")

        # 6jc. Test Mutation: setProductPrice (selling_price = 999.99)
        print("\n--- Test Mutation: setProductPrice (selling_price) ---")
        set_price_mutation = """
            mutation SetProductPrice($input: SetProductPriceInput!) {
                setProductPrice(input: $input) {
                    id
                    price
                    productId
                    pricingTypeId
                }
            }
        """
        result = await schema.execute(
            set_price_mutation,
            variable_values={
                "input": {
                    "productId": prod1["id"],
                    "pricingTypeId": pt_selling["id"],
                    "price": 999.99
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SetProductPrice selling_price Error: {result.errors}")
            return
        price_selling = result.data["setProductPrice"]
        print(f"Product Price set: {price_selling['price']} for pricingTypeId={price_selling['pricingTypeId']}")
        assert price_selling["price"] == 999.99

        # 6jd. Test Mutation: setProductPrice (cost = 500.00)
        print("\n--- Test Mutation: setProductPrice (cost) ---")
        result = await schema.execute(
            set_price_mutation,
            variable_values={
                "input": {
                    "productId": prod1["id"],
                    "pricingTypeId": pt_cost["id"],
                    "price": 500.00
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SetProductPrice cost Error: {result.errors}")
            return
        price_cost = result.data["setProductPrice"]
        print(f"Product Price set: {price_cost['price']} for pricingTypeId={price_cost['pricingTypeId']}")

        # 6je. Test Query: product(id) resolving default price and complete prices relation
        print("\n--- Test Query: product details (resolving default price & prices list) ---")
        query_prod_prices = """
            query GetProductPrices($id: UUID!) {
                product(id: $id) {
                    id
                    title
                    price
                    prices {
                        id
                        price
                        pricingType {
                            id
                            type
                        }
                    }
                }
            }
        """
        result = await schema.execute(
            query_prod_prices,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query product prices Error: {result.errors}")
            return
        prod_resolved = result.data["product"]
        print(f"Resolved product: price={prod_resolved['price']} (Expected default selling_price: 999.99)")
        assert prod_resolved["price"] == 999.99, "Default price should match selling_price"
        assert len(prod_resolved["prices"]) == 2, "Expected 2 price mappings"

        # 6jf. Test Mutation: deleteProductPrice (selling_price)
        print("\n--- Test Mutation: deleteProductPrice (selling_price) ---")
        delete_price_mutation = """
            mutation DeleteProductPrice($productId: UUID!, $pricingTypeId: UUID!) {
                deleteProductPrice(productId: $productId, pricingTypeId: $pricingTypeId)
            }
        """
        result = await schema.execute(
            delete_price_mutation,
            variable_values={
                "productId": prod1["id"],
                "pricingTypeId": pt_selling["id"]
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"DeleteProductPrice Error: {result.errors}")
            return
        del_ok = result.data["deleteProductPrice"]
        print(f"Product Price mapping deleted: {del_ok}")
        assert del_ok is True

        # Verify that default price is now None since selling_price was deleted
        result = await schema.execute(
            query_prod_prices,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        prod_resolved2 = result.data["product"]
        print(f"Resolved product price after deleting selling_price: {prod_resolved2['price']}")
        assert prod_resolved2["price"] is None, "Default price should be None now"
        assert len(prod_resolved2["prices"]) == 1, "Should only have 1 price mapping left (cost)"

        # 6k. Test Mutation: createProduct (Duplicate SKU error)
        print("\n--- Test Mutation: createProduct (Duplicate SKU - Expected to Fail) ---")
        variables_prod_dup = {
            "input": {
                "title": "Duplicate SKU Product",
                "productType": "GOODS",
                "sku": f"PROD-LAPTOP-{rand_id}"  # Same SKU as prod1
            }
        }
        result = await schema.execute(
            create_product_mutation,
            variable_values=variables_prod_dup,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: Duplicate SKU creation failed as expected: {result.errors[0].message}")
        else:
            print("Failure: Duplicate SKU creation succeeded unexpectedly!")
            return

        # 6ka. Test Mutation: createAttribute (Color)
        print("\n--- Test Mutation: createAttribute (Color) ---")
        create_attr_mutation = """
            mutation CreateAttribute($input: CreateAttributeInput!) {
                createAttribute(input: $input) {
                    id
                    name
                    displayName
                }
            }
        """
        result = await schema.execute(
            create_attr_mutation,
            variable_values={"input": {"name": "color", "displayName": "Color"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateAttribute Color Error: {result.errors}")
            return
        attr_color = result.data["createAttribute"]
        print(f"Attribute Color Created: ID={attr_color['id']}")
        assert attr_color["name"] == "color"
        assert attr_color["displayName"] == "Color"

        # 6kb. Test Mutation: createAttribute (Size)
        print("\n--- Test Mutation: createAttribute (Size) ---")
        result = await schema.execute(
            create_attr_mutation,
            variable_values={"input": {"name": "size", "displayName": "Size"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateAttribute Size Error: {result.errors}")
            return
        attr_size = result.data["createAttribute"]
        print(f"Attribute Size Created: ID={attr_size['id']}")

        # 6kc. Test Mutation: createAttribute (Duplicate Name - Expected to Fail)
        print("\n--- Test Mutation: createAttribute (Duplicate Name - Expected to Fail) ---")
        result = await schema.execute(
            create_attr_mutation,
            variable_values={"input": {"name": "color", "displayName": "Colour"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: Duplicate Attribute creation failed as expected: {result.errors[0].message}")
        else:
            print("Failure: Duplicate Attribute creation succeeded unexpectedly!")
            return

        # 6kd. Test Mutation: createAttributeValue (Red under Color)
        print("\n--- Test Mutation: createAttributeValue (Red under Color) ---")
        create_val_mutation = """
            mutation CreateAttributeValue($input: CreateAttributeValueInput!) {
                createAttributeValue(input: $input) {
                    id
                    attributeId
                    value
                    hexCode
                }
            }
        """
        result = await schema.execute(
            create_val_mutation,
            variable_values={
                "input": {
                    "attributeId": attr_color["id"],
                    "value": "Red",
                    "hexCode": "#FF0000"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateAttributeValue Red Error: {result.errors}")
            return
        val_red = result.data["createAttributeValue"]
        print(f"Attribute Value Red Created: ID={val_red['id']}")
        assert val_red["value"] == "Red"
        assert val_red["hexCode"] == "#FF0000"

        # 6ke. Test Mutation: createAttributeValue (Blue under Color)
        print("\n--- Test Mutation: createAttributeValue (Blue under Color) ---")
        result = await schema.execute(
            create_val_mutation,
            variable_values={
                "input": {
                    "attributeId": attr_color["id"],
                    "value": "Blue",
                    "hexCode": "#0000FF"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateAttributeValue Blue Error: {result.errors}")
            return
        val_blue = result.data["createAttributeValue"]
        print(f"Attribute Value Blue Created: ID={val_blue['id']}")

        # 6kf. Test Mutation: createAttributeValue (Duplicate Value - Expected to Fail)
        print("\n--- Test Mutation: createAttributeValue (Duplicate Value - Expected to Fail) ---")
        result = await schema.execute(
            create_val_mutation,
            variable_values={
                "input": {
                    "attributeId": attr_color["id"],
                    "value": "Red"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: Duplicate AttributeValue creation failed as expected: {result.errors[0].message}")
        else:
            print("Failure: Duplicate AttributeValue creation succeeded unexpectedly!")
            return

        # 6kg. Test Mutation: createAttributeValue (XL under Size)
        print("\n--- Test Mutation: createAttributeValue (XL under Size) ---")
        result = await schema.execute(
            create_val_mutation,
            variable_values={
                "input": {
                    "attributeId": attr_size["id"],
                    "value": "XL"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateAttributeValue XL Error: {result.errors}")
            return
        val_xl = result.data["createAttributeValue"]
        print(f"Attribute Value XL Created: ID={val_xl['id']}")

        # 6kh. Test Mutation: assignAttributeValueToProduct (Red to Variant)
        print("\n--- Test Mutation: assignAttributeValueToProduct (Red to Variant) ---")
        assign_mutation = """
            mutation AssignAttributeValueToProduct($productId: UUID!, $attributeValueId: UUID!) {
                assignAttributeValueToProduct(productId: $productId, attributeValueId: $attributeValueId) {
                    id
                    productId
                    attributeValueId
                }
            }
        """
        result = await schema.execute(
            assign_mutation,
            variable_values={
                "productId": prod2["id"],
                "attributeValueId": val_red["id"]
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Assign Red Error: {result.errors}")
            return
        print("Successfully assigned Red color to Laptop variant.")

        # 6ki. Test Mutation: assignAttributeValueToProduct (XL to Variant)
        print("\n--- Test Mutation: assignAttributeValueToProduct (XL to Variant) ---")
        result = await schema.execute(
            assign_mutation,
            variable_values={
                "productId": prod2["id"],
                "attributeValueId": val_xl["id"]
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Assign XL Error: {result.errors}")
            return
        print("Successfully assigned XL size to Laptop variant.")

        # 6kj. Test Query: product details with attributes mapping
        print("\n--- Test Query: product details with attributes ---")
        query_prod_attributes = """
            query GetProductAttributes($id: UUID!) {
                product(id: $id) {
                    id
                    title
                    attributes {
                        id
                        attributeValue {
                            id
                            value
                            hexCode
                            attribute {
                                id
                                name
                                displayName
                            }
                        }
                    }
                }
            }
        """
        result = await schema.execute(
            query_prod_attributes,
            variable_values={"id": prod2["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query product attributes Error: {result.errors}")
            return
        prod_attrs = result.data["product"]["attributes"]
        print(f"Resolved product attributes: {len(prod_attrs)}")
        assert len(prod_attrs) == 2, "Expected 2 attribute mappings assigned to product"
        # Validate values
        values_list = [a["attributeValue"]["value"] for a in prod_attrs]
        assert "Red" in values_list
        assert "XL" in values_list

        # 6kk. Test Mutation: removeAttributeValueFromProduct (Red from Variant)
        print("\n--- Test Mutation: removeAttributeValueFromProduct (Red from Variant) ---")
        remove_mutation = """
            mutation RemoveAttributeValueFromProduct($productId: UUID!, $attributeValueId: UUID!) {
                removeAttributeValueFromProduct(productId: $productId, attributeValueId: $attributeValueId)
            }
        """
        result = await schema.execute(
            remove_mutation,
            variable_values={
                "productId": prod2["id"],
                "attributeValueId": val_red["id"]
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Remove Red Error: {result.errors}")
            return
        assert result.data["removeAttributeValueFromProduct"] is True
        print("Successfully removed Red color from Laptop variant.")

        # Verify product now only has XL size mapping
        result = await schema.execute(
            query_prod_attributes,
            variable_values={"id": prod2["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        prod_attrs_after = result.data["product"]["attributes"]
        assert len(prod_attrs_after) == 1
        assert prod_attrs_after[0]["attributeValue"]["value"] == "XL"

        # 6kl. Test Mutation: createProductGroup
        print("\n--- Test Mutation: createProductGroup ---")
        create_group_mutation = """
            mutation CreateProductGroup($input: CreateProductGroupInput!) {
                createProductGroup(input: $input) {
                    id
                    name
                    description
                }
            }
        """
        result = await schema.execute(
            create_group_mutation,
            variable_values={"input": {"name": "Summer Electronics", "description": "Laptops and accessories"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateProductGroup Error: {result.errors}")
            return
        group = result.data["createProductGroup"]
        print(f"Product Group Created: ID={group['id']}, Name={group['name']}")
        assert group["name"] == "Summer Electronics"

        # 6km. Test Mutation: createProductGroup (Duplicate - Expected to Fail)
        print("\n--- Test Mutation: createProductGroup (Duplicate - Expected to Fail) ---")
        result = await schema.execute(
            create_group_mutation,
            variable_values={"input": {"name": "Summer Electronics"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: Duplicate group creation failed as expected: {result.errors[0].message}")
        else:
            print("Failure: Duplicate group creation succeeded unexpectedly!")
            return

        # 6kn. Test Mutation: linkProductToGroup (prod1)
        print("\n--- Test Mutation: linkProductToGroup (prod1) ---")
        link_mutation = """
            mutation LinkProductToGroup($productId: UUID!, $groupId: UUID!) {
                linkProductToGroup(productId: $productId, groupId: $groupId) {
                    id
                    productId
                    groupId
                }
            }
        """
        result = await schema.execute(
            link_mutation,
            variable_values={"productId": prod1["id"], "groupId": group["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Link prod1 to group Error: {result.errors}")
            return
        print("Successfully linked prod1 to group.")

        # 6ko. Test Mutation: linkProductToGroup (prod2)
        print("\n--- Test Mutation: linkProductToGroup (prod2) ---")
        result = await schema.execute(
            link_mutation,
            variable_values={"productId": prod2["id"], "groupId": group["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Link prod2 to group Error: {result.errors}")
            return
        print("Successfully linked prod2 to group.")

        # 6kp. Test Query: productGroups list
        print("\n--- Test Query: productGroups list ---")
        query_groups = """
            query GetProductGroups {
                productGroups {
                    id
                    name
                    products {
                        id
                        title
                    }
                }
            }
        """
        result = await schema.execute(
            query_groups,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"GetProductGroups Error: {result.errors}")
            return
        groups_list = result.data["productGroups"]
        assert len(groups_list) == 1
        assert len(groups_list[0]["products"]) == 2
        print(f"Verified group contains both products: {[p['title'] for p in groups_list[0]['products']]}")

        # 6kq. Test Query: product with relatedProducts resolver
        print("\n--- Test Query: product relatedProducts ---")
        query_related = """
            query GetRelatedProducts($id: UUID!) {
                product(id: $id) {
                    id
                    title
                    relatedProducts {
                        id
                        title
                    }
                }
            }
        """
        result = await schema.execute(
            query_related,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query relatedProducts Error: {result.errors}")
            return
        related_prods = result.data["product"]["relatedProducts"]
        print(f"Related products for prod1: {[p['title'] for p in related_prods]}")
        assert len(related_prods) == 1
        assert related_prods[0]["id"] == prod2["id"]

        # 6kr. Test Mutation: unlinkProductFromGroup (prod2)
        print("\n--- Test Mutation: unlinkProductFromGroup (prod2) ---")
        unlink_mutation = """
            mutation UnlinkProductFromGroup($productId: UUID!, $groupId: UUID!) {
                unlinkProductFromGroup(productId: $productId, groupId: $groupId)
            }
        """
        result = await schema.execute(
            unlink_mutation,
            variable_values={"productId": prod2["id"], "groupId": group["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Unlink prod2 from group Error: {result.errors}")
            return
        assert result.data["unlinkProductFromGroup"] is True
        print("Successfully unlinked prod2 from group.")

        # Verify relatedProducts is now empty
        result = await schema.execute(
            query_related,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert len(result.data["product"]["relatedProducts"]) == 0
        print("Verified relatedProducts is empty after unlinking.")

        # 6ks. Test Mutation: deleteProductGroup
        print("\n--- Test Mutation: deleteProductGroup ---")
        delete_group_mutation = """
            mutation DeleteProductGroup($id: UUID!) {
                deleteProductGroup(id: $id)
            }
        """
        result = await schema.execute(
            delete_group_mutation,
            variable_values={"id": group["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Delete product group Error: {result.errors}")
            return
        assert result.data["deleteProductGroup"] is True
        print("Successfully deleted product group.")

        # 6l. Test Query: products (List)
        print("\n--- Test Query: products (List all) ---")
        query_products = """
            query GetProducts($productType: ProductTypeEnum, $search: String) {
                products(productType: $productType, search: $search) {
                    id
                    title
                    sku
                    productType
                }
            }
        """
        result = await schema.execute(
            query_products,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query Products Error: {result.errors}")
            return
        products_list = result.data["products"]
        print(f"Fetched {len(products_list)} products.")
        assert len(products_list) >= 2, "Expected at least 2 products in DB"

        # 6m. Test Query: products (Search filter)
        print("\n--- Test Query: products (Search filter) ---")
        result = await schema.execute(
            query_products,
            variable_values={"search": "Laptop"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query Products Search Error: {result.errors}")
            return
        searched_products = result.data["products"]
        print(f"Searched 'Laptop': found {len(searched_products)} matching products.")
        assert len(searched_products) == 2, "Search for 'Laptop' should return both products"

        # 6n. Test Query: product(id) resolving parent and children relations
        print("\n--- Test Query: product(id) with relations ---")
        query_single_product = """
            query GetProduct($id: UUID!) {
                product(id: $id) {
                    id
                    title
                    parent {
                        id
                        title
                    }
                    children {
                        id
                        title
                    }
                }
            }
        """
        # Fetch child product and resolve parent
        result = await schema.execute(
            query_single_product,
            variable_values={"id": prod2["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query child product Error: {result.errors}")
            return
        child_resolved = result.data["product"]
        print(f"Child Product resolved: parent.title='{child_resolved['parent']['title']}'")
        assert child_resolved["parent"]["id"] == prod1["id"], "Parent ID mismatch on child resolver"

        # Fetch parent product and resolve children
        result = await schema.execute(
            query_single_product,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query parent product Error: {result.errors}")
            return
        parent_resolved = result.data["product"]
        print(f"Parent Product resolved: children count={len(parent_resolved['children'])}")
        assert any(c["id"] == prod2["id"] for c in parent_resolved["children"]), "Child product not found in children list"

        # 6o. Test Mutation: updateProduct
        print("\n--- Test Mutation: updateProduct ---")
        update_product_mutation = """
            mutation UpdateProduct($id: UUID!, $input: UpdateProductInput!) {
                updateProduct(id: $id, input: $input) {
                    id
                    title
                    subtitle
                }
            }
        """
        result = await schema.execute(
            update_product_mutation,
            variable_values={
                "id": prod1["id"],
                "input": {
                    "subtitle": "Super high-end developer laptop",
                    "title": "Professional E-Commerce Laptop v2"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateProduct Error: {result.errors}")
            return
        prod1_updated = result.data["updateProduct"]
        print(f"Product updated: title='{prod1_updated['title']}', subtitle='{prod1_updated['subtitle']}'")
        assert prod1_updated["title"] == "Professional E-Commerce Laptop v2"
        assert prod1_updated["subtitle"] == "Super high-end developer laptop"

        # 6o_media. Test Media Integration
        print("\n--- Test Mutation: createMedia (User avatar) ---")
        create_media_mutation = """
            mutation CreateMedia($input: CreateMediaInput!) {
                createMedia(input: $input) {
                    id
                    filePath
                    mediaUrl
                    mediaType
                    fileExtension
                    altText
                    metaAttributes
                    entityName
                    entityId
                }
            }
        """
        user_avatar_variables = {
            "input": {
                "filePath": "/uploads/user_avatar.png",
                "mediaUrl": "https://example.com/uploads/user_avatar.png",
                "mediaType": "IMAGE",
                "fileExtension": "png",
                "altText": "User Avatar",
                "metaAttributes": {"width": 200, "height": 200, "size": 15240},
                "entityName": "user",
                "entityId": user_data["id"]
            }
        }
        result = await schema.execute(
            create_media_mutation,
            variable_values=user_avatar_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateMedia User Avatar Error: {result.errors}")
            return
        media_user = result.data["createMedia"]
        print(f"Media created for User: ID={media_user['id']}, filePath={media_user['filePath']}, metaAttributes={media_user['metaAttributes']}")
        assert media_user["entityName"] == "user"
        assert media_user["entityId"] == user_data["id"]
        assert media_user["metaAttributes"]["width"] == 200

        print("\n--- Test Mutation: createMedia (Product image) ---")
        product_image_variables = {
            "input": {
                "filePath": "/uploads/product_img.jpg",
                "mediaUrl": "https://example.com/uploads/product_img.jpg",
                "mediaType": "IMAGE",
                "fileExtension": "jpg",
                "altText": "Laptop Image",
                "metaAttributes": {"width": 800, "height": 600, "size": 125430},
                "entityName": "product",
                "entityId": prod1["id"]
            }
        }
        result = await schema.execute(
            create_media_mutation,
            variable_values=product_image_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateMedia Product Image Error: {result.errors}")
            return
        media_product = result.data["createMedia"]
        print(f"Media created for Product: ID={media_product['id']}, filePath={media_product['filePath']}")
        assert media_product["entityName"] == "product"
        assert media_product["entityId"] == prod1["id"]

        print("\n--- Test Query: me resolving media relation ---")
        query_me_media = """
            query {
                me {
                    id
                    media {
                        id
                        filePath
                        mediaUrl
                        metaAttributes
                    }
                }
            }
        """
        result = await schema.execute(
            query_me_media,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query me media Error: {result.errors}")
            return
        me_with_media = result.data["me"]
        print(f"Me media resolved: count={len(me_with_media['media'])}")
        assert len(me_with_media["media"]) == 1, "Expected 1 media record resolved for user"
        assert me_with_media["media"][0]["id"] == media_user["id"]

        print("\n--- Test Query: product resolving media relation ---")
        query_product_media = """
            query GetProductMedia($id: UUID!) {
                product(id: $id) {
                    id
                    thumbnail {
                        id
                        filePath
                    }
                    media {
                        id
                        filePath
                        mediaUrl
                    }
                }
            }
        """
        result = await schema.execute(
            query_product_media,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query product media Error: {result.errors}")
            return
        prod_with_media = result.data["product"]
        print(f"Product media resolved: count={len(prod_with_media['media'])}")
        assert len(prod_with_media["media"]) == 1, "Expected 1 media record resolved for product"
        assert prod_with_media["media"][0]["id"] == media_product["id"]

        print("\n--- Test Mutation: updateProduct setting thumbnailMediaId ---")
        update_product_thumbnail_mutation = """
            mutation UpdateProductThumbnail($id: UUID!, $input: UpdateProductInput!) {
                updateProduct(id: $id, input: $input) {
                    id
                    thumbnailMediaId
                }
            }
        """
        result = await schema.execute(
            update_product_thumbnail_mutation,
            variable_values={
                "id": prod1["id"],
                "input": {
                    "thumbnailMediaId": media_product["id"]
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Update product thumbnail error: {result.errors}")
            return
        prod_updated_thumbnail = result.data["updateProduct"]
        print(f"Product thumbnail updated: {prod_updated_thumbnail['thumbnailMediaId']}")
        assert prod_updated_thumbnail["thumbnailMediaId"] == media_product["id"]

        # Verify product resolves thumbnail now
        result = await schema.execute(
            query_product_media,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query product media after thumbnail update error: {result.errors}")
            return
        prod_resolved_thumbnail = result.data["product"]
        print(f"Product thumbnail resolved: ID={prod_resolved_thumbnail['thumbnail']['id']}")
        assert prod_resolved_thumbnail["thumbnail"]["id"] == media_product["id"]

        print("\n--- Test Query: mediaList (filter by entityName and entityId) ---")
        query_media_list = """
            query GetMediaList($entityName: String, $entityId: UUID) {
                mediaList(entityName: $entityName, entityId: $entityId) {
                    id
                    filePath
                    entityName
                    entityId
                }
            }
        """
        result = await schema.execute(
            query_media_list,
            variable_values={"entityName": "product", "entityId": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Query mediaList Error: {result.errors}")
            return
        med_list = result.data["mediaList"]
        print(f"mediaList resolved: count={len(med_list)}")
        assert len(med_list) == 1
        assert med_list[0]["id"] == media_product["id"]

        print("\n--- Test Mutation: updateMedia ---")
        update_media_mutation = """
            mutation UpdateMedia($id: UUID!, $input: UpdateMediaInput!) {
                updateMedia(id: $id, input: $input) {
                    id
                    altText
                    metaAttributes
                }
            }
        """
        result = await schema.execute(
            update_media_mutation,
            variable_values={
                "id": media_product["id"],
                "input": {
                    "altText": "Updated Laptop Image Alt Text",
                    "metaAttributes": {"width": 1024, "height": 768, "size": 204800}
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateMedia Error: {result.errors}")
            return
        updated_media = result.data["updateMedia"]
        print(f"Media updated: altText='{updated_media['altText']}', metaAttributes={updated_media['metaAttributes']}")
        assert updated_media["altText"] == "Updated Laptop Image Alt Text"
        assert updated_media["metaAttributes"]["width"] == 1024

        print("\n--- Test Mutation: deleteMedia ---")
        delete_media_mutation = """
            mutation DeleteMedia($id: UUID!) {
                deleteMedia(id: $id)
            }
        """
        result = await schema.execute(
            delete_media_mutation,
            variable_values={"id": media_user["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"DeleteMedia user avatar Error: {result.errors}")
            return
        del_user_avatar_ok = result.data["deleteMedia"]
        print(f"User avatar deleted: {del_user_avatar_ok}")
        assert del_user_avatar_ok is True

        # Verify user media list is empty now
        result = await schema.execute(
            query_me_media,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert len(result.data["me"]["media"]) == 0, "User media should be empty after deletion"

        # Also delete product media
        result = await schema.execute(
            delete_media_mutation,
            variable_values={"id": media_product["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert result.data["deleteMedia"] is True

        # 6o_nested_media. Test Nested Media Creation & Editing
        print("\n--- Test Mutation: createProduct with nested media ---")
        create_product_nested_mutation = """
            mutation CreateProductNested($input: CreateProductInput!) {
                createProduct(input: $input) {
                    id
                    title
                    sku
                    media {
                        id
                        filePath
                        mediaUrl
                    }
                }
            }
        """
        nested_product_variables = {
            "input": {
                "title": "Nested Media Laptop",
                "productType": "GOODS",
                "sku": f"PROD-NESTED-{rand_id}",
                "media": [
                    {
                        "filePath": "/uploads/nested_laptop_1.jpg",
                        "mediaUrl": "https://example.com/uploads/nested_laptop_1.jpg",
                        "mediaType": "IMAGE",
                        "fileExtension": "jpg",
                        "altText": "Nested Laptop View 1",
                        "metaAttributes": {"size": 45000}
                    }
                ]
            }
        }
        result = await schema.execute(
            create_product_nested_mutation,
            variable_values=nested_product_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateProductNested Error: {result.errors}")
            return
        nested_prod = result.data["createProduct"]
        print(f"Created product: ID={nested_prod['id']}, title='{nested_prod['title']}'")
        assert len(nested_prod["media"]) == 1
        assert nested_prod["media"][0]["filePath"] == "/uploads/nested_laptop_1.jpg"

        print("\n--- Test Mutation: updateProduct with nested media ---")
        update_product_nested_mutation = """
            mutation UpdateProductNested($id: UUID!, $input: UpdateProductInput!) {
                updateProduct(id: $id, input: $input) {
                    id
                    title
                    media {
                        id
                        filePath
                        mediaUrl
                    }
                }
            }
        """
        nested_product_update_variables = {
            "id": nested_prod["id"],
            "input": {
                "title": "Nested Media Laptop Updated",
                "media": [
                    {
                        "filePath": "/uploads/nested_laptop_new1.jpg",
                        "mediaUrl": "https://example.com/uploads/nested_laptop_new1.jpg",
                        "mediaType": "IMAGE",
                        "fileExtension": "jpg",
                        "altText": "Updated view 1",
                        "metaAttributes": {"size": 50000}
                    },
                    {
                        "filePath": "/uploads/nested_laptop_new2.jpg",
                        "mediaUrl": "https://example.com/uploads/nested_laptop_new2.jpg",
                        "mediaType": "IMAGE",
                        "fileExtension": "jpg",
                        "altText": "Updated view 2",
                        "metaAttributes": {"size": 60000}
                    }
                ]
            }
        }
        result = await schema.execute(
            update_product_nested_mutation,
            variable_values=nested_product_update_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateProductNested Error: {result.errors}")
            return
        updated_prod = result.data["updateProduct"]
        print(f"Updated product: title='{updated_prod['title']}', media count={len(updated_prod['media'])}")
        assert updated_prod["title"] == "Nested Media Laptop Updated"
        assert len(updated_prod["media"]) == 2
        file_paths = [m["filePath"] for m in updated_prod["media"]]
        assert "/uploads/nested_laptop_new1.jpg" in file_paths
        assert "/uploads/nested_laptop_new2.jpg" in file_paths
        assert "/uploads/nested_laptop_1.jpg" not in file_paths

        print("\n--- Test Mutation: createUser with nested media ---")
        create_user_nested_mutation = """
            mutation CreateUserNested($input: CreateUserInput!) {
                createUser(input: $input) {
                    id
                    name
                    email
                    mobilenumber
                    media {
                        id
                        filePath
                        mediaUrl
                    }
                }
            }
        """
        nested_user_variables = {
            "input": {
                "name": "Nested Media User",
                "mobilenumber": f"991122{rand_id}",
                "email": f"nested_{rand_id}@example.com",
                "password": "Password123!",
                "role": "USER",
                "media": [
                    {
                        "filePath": "/uploads/user_doc.pdf",
                        "mediaUrl": "https://example.com/uploads/user_doc.pdf",
                        "mediaType": "PDF",
                        "fileExtension": "pdf",
                        "altText": "Verification Doc",
                        "metaAttributes": {"pages": 3}
                    }
                ]
            }
        }
        result = await schema.execute(
            create_user_nested_mutation,
            variable_values=nested_user_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateUserNested Error: {result.errors}")
            return
        nested_user = result.data["createUser"]
        print(f"Created user: ID={nested_user['id']}, name='{nested_user['name']}'")
        assert len(nested_user["media"]) == 1
        assert nested_user["media"][0]["filePath"] == "/uploads/user_doc.pdf"

        print("\n--- Test Mutation: updateUser with nested media ---")
        update_user_nested_mutation = """
            mutation UpdateUserNested($id: UUID!, $input: UpdateUserInput!) {
                updateUser(id: $id, input: $input) {
                    id
                    name
                    email
                    media {
                        id
                        filePath
                        mediaUrl
                    }
                }
            }
        """
        nested_user_update_variables = {
            "id": nested_user["id"],
            "input": {
                "name": "Nested Media User Updated",
                "email": f"nested_upd_{rand_id}@example.com",
                "media": [
                    {
                        "filePath": "/uploads/user_avatar_new.jpg",
                        "mediaUrl": "https://example.com/uploads/user_avatar_new.jpg",
                        "mediaType": "IMAGE",
                        "fileExtension": "jpg",
                        "altText": "New Avatar",
                        "metaAttributes": {"size": 25000}
                    }
                ]
            }
        }
        result = await schema.execute(
            update_user_nested_mutation,
            variable_values=nested_user_update_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateUserNested Error: {result.errors}")
            return
        updated_user = result.data["updateUser"]
        print(f"Updated user: name='{updated_user['name']}', media count={len(updated_user['media'])}")
        assert updated_user["name"] == "Nested Media User Updated"
        assert updated_user["email"] == f"nested_upd_{rand_id}@example.com"
        assert len(updated_user["media"]) == 1
        assert updated_user["media"][0]["filePath"] == "/uploads/user_avatar_new.jpg"

        # Cleanup nested product
        delete_product_mutation_local = """
            mutation DeleteProduct($id: UUID!) {
                deleteProduct(id: $id)
            }
        """
        result = await schema.execute(
            delete_product_mutation_local,
            variable_values={"id": nested_prod["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert result.data["deleteProduct"] is True

        # 6q_categories. Test Category CRUD & Product Association
        print("\n--- Test Mutation: createCategory (Parent) ---")
        create_category_mutation = """
            mutation CreateCategory($input: CreateCategoryInput!) {
                createCategory(input: $input) {
                    id
                    title
                    sku
                    media {
                        id
                        filePath
                    }
                }
            }
        """
        cat_parent_variables = {
            "input": {
                "title": "Electronics",
                "sku": f"CAT-ELEC-{rand_id}",
                "media": [
                    {
                        "filePath": "/uploads/electronics.jpg",
                        "mediaUrl": "https://example.com/uploads/electronics.jpg",
                        "mediaType": "IMAGE",
                        "altText": "Electronics Banner"
                    }
                ]
            }
        }
        result = await schema.execute(
            create_category_mutation,
            variable_values=cat_parent_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateCategory Parent Error: {result.errors}")
            return
        cat_parent = result.data["createCategory"]
        print(f"Parent Category created: ID={cat_parent['id']}, title='{cat_parent['title']}'")
        assert cat_parent["sku"] == f"CAT-ELEC-{rand_id}"
        assert len(cat_parent["media"]) == 1

        print("\n--- Test Mutation: createCategory (Child) ---")
        cat_child_variables = {
            "input": {
                "title": "Laptops",
                "sku": f"CAT-LAP-{rand_id}",
                "parentId": cat_parent["id"]
            }
        }
        result = await schema.execute(
            create_category_mutation,
            variable_values=cat_child_variables,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateCategory Child Error: {result.errors}")
            return
        cat_child = result.data["createCategory"]
        print(f"Child Category created: ID={cat_child['id']}, parentId={cat_parent['id']}")

        print("\n--- Test Query: category resolving parent and children relation ---")
        query_category_details = """
            query GetCategory($id: UUID!) {
                category(id: $id) {
                    id
                    title
                    parent {
                        id
                        title
                    }
                    children {
                        id
                        title
                    }
                }
            }
        """
        # Fetch parent and check children
        result = await schema.execute(
            query_category_details,
            variable_values={"id": cat_parent["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        parent_resolved = result.data["category"]
        print(f"Parent category children count={len(parent_resolved['children'])}")
        assert len(parent_resolved["children"]) == 1
        assert parent_resolved["children"][0]["id"] == cat_child["id"]

        print("\n--- Test Mutation: setProductCategories ---")
        set_prod_cats_mutation = """
            mutation SetProductCategories($productId: UUID!, $categoryIds: [UUID!]!) {
                setProductCategories(productId: $productId, categoryIds: $categoryIds) {
                    id
                    title
                }
            }
        """
        result = await schema.execute(
            set_prod_cats_mutation,
            variable_values={
                "productId": prod1["id"],
                "categoryIds": [cat_parent["id"], cat_child["id"]]
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SetProductCategories Error: {result.errors}")
            return
        assoc_cats = result.data["setProductCategories"]
        print(f"Associated {len(assoc_cats)} categories with product {prod1['id']}")
        assert len(assoc_cats) == 2

        print("\n--- Test Query: product resolving categories relation ---")
        query_prod_categories = """
            query GetProductCategories($id: UUID!) {
                product(id: $id) {
                    id
                    title
                    categories {
                        id
                        title
                    }
                }
            }
        """
        result = await schema.execute(
            query_prod_categories,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        prod_resolved = result.data["product"]
        print(f"Product categories count={len(prod_resolved['categories'])}")
        assert len(prod_resolved["categories"]) == 2
        resolved_cat_ids = [c["id"] for c in prod_resolved["categories"]]
        assert cat_parent["id"] in resolved_cat_ids
        assert cat_child["id"] in resolved_cat_ids

        print("\n--- Test Query: category resolving products relation ---")
        query_category_products = """
            query GetCategoryProducts($id: UUID!) {
                category(id: $id) {
                    id
                    products {
                        id
                        title
                    }
                }
            }
        """
        result = await schema.execute(
            query_category_products,
            variable_values={"id": cat_child["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        cat_child_resolved = result.data["category"]
        print(f"Category child products count={len(cat_child_resolved['products'])}")
        assert len(cat_child_resolved["products"]) == 1
        assert cat_child_resolved["products"][0]["id"] == prod1["id"]

        print("\n--- Test Query: categories (List with search) ---")
        query_categories_list = """
            query GetCategories($search: String) {
                categories(search: $search) {
                    id
                    title
                }
            }
        """
        result = await schema.execute(
            query_categories_list,
            variable_values={"search": "ELEC"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        search_res = result.data["categories"]
        print(f"Search for 'ELEC' found {len(search_res)} categories")
        assert len(search_res) == 1
        assert search_res[0]["id"] == cat_parent["id"]

        print("\n--- Test Mutation: updateCategory with media ---")
        update_category_mutation = """
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
        """
        result = await schema.execute(
            update_category_mutation,
            variable_values={
                "id": cat_child["id"],
                "input": {
                    "title": "Laptops & Notebooks",
                    "media": [
                        {
                            "filePath": "/uploads/notebooks.jpg",
                            "mediaUrl": "https://example.com/uploads/notebooks.jpg",
                            "mediaType": "IMAGE"
                        }
                    ]
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"UpdateCategory Error: {result.errors}")
            return
        cat_child_updated = result.data["updateCategory"]
        print(f"Category updated title='{cat_child_updated['title']}', media count={len(cat_child_updated['media'])}")
        assert cat_child_updated["title"] == "Laptops & Notebooks"
        assert len(cat_child_updated["media"]) == 1
        assert cat_child_updated["media"][0]["filePath"] == "/uploads/notebooks.jpg"

        print("\n--- Test Mutation: deleteCategory ---")
        delete_category_mutation = """
            mutation DeleteCategory($id: UUID!) {
                deleteCategory(id: $id)
            }
        """
        result = await schema.execute(
            delete_category_mutation,
            variable_values={"id": cat_child["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert result.data["deleteCategory"] is True

        # Verify parent no longer has children
        result = await schema.execute(
            query_category_details,
            variable_values={"id": cat_parent["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert len(result.data["category"]["children"]) == 0

        # Verify product categories list only has parent now
        result = await schema.execute(
            query_prod_categories,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert len(result.data["product"]["categories"]) == 1
        assert result.data["product"]["categories"][0]["id"] == cat_parent["id"]

        # 6q. Test Shopping Cart System
        print("\n--- Test Mutation: myCart (initial empty cart) ---")
        my_cart_query = """
            query {
                myCart {
                    id
                    userId
                    items {
                        id
                        quantity
                        productId
                        product {
                            id
                            title
                        }
                    }
                }
            }
        """
        result = await schema.execute(
            my_cart_query,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"myCart Query Error: {result.errors}")
            return
        
        cart_data = result.data["myCart"]
        print(f"Cart initialized successfully: ID={cart_data['id']}, items count={len(cart_data['items'])}")
        assert len(cart_data["items"]) == 0
        
        # Test add to cart
        print("\n--- Test Mutation: addToCart ---")
        add_to_cart_mutation = """
            mutation AddToCart($productId: UUID!, $quantity: Int!) {
                addToCart(productId: $productId, quantity: $quantity) {
                    id
                    items {
                        id
                        quantity
                        productId
                        product {
                            id
                            title
                        }
                    }
                }
            }
        """
        result = await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": prod1["id"], "quantity": 2},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"addToCart Mutation Error: {result.errors}")
            return
        
        cart_data = result.data["addToCart"]
        print(f"Added product to cart, items count={len(cart_data['items'])}")
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["quantity"] == 2
        assert cart_data["items"][0]["productId"] == prod1["id"]
        assert cart_data["items"][0]["product"]["title"] == "Professional E-Commerce Laptop v2"
        
        # Test add duplicate to cart (increment quantity)
        print("\n--- Test Mutation: addToCart (duplicate increment) ---")
        result = await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": prod1["id"], "quantity": 3},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["addToCart"]
        print(f"Added duplicate to cart, updated quantity={cart_data['items'][0]['quantity']}")
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["quantity"] == 5

        # Test update cart item quantity
        print("\n--- Test Mutation: updateCartItem ---")
        update_cart_item_mutation = """
            mutation UpdateCartItem($productId: UUID!, $quantity: Int!) {
                updateCartItem(productId: $productId, quantity: $quantity) {
                    id
                    items {
                        id
                        quantity
                        productId
                    }
                }
            }
        """
        result = await schema.execute(
            update_cart_item_mutation,
            variable_values={"productId": prod1["id"], "quantity": 4},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["updateCartItem"]
        print(f"Updated cart item, new quantity={cart_data['items'][0]['quantity']}")
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["quantity"] == 4

        # Test update cart item quantity to 0 (delete)
        print("\n--- Test Mutation: updateCartItem (delete by setting 0) ---")
        result = await schema.execute(
            update_cart_item_mutation,
            variable_values={"productId": prod1["id"], "quantity": 0},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["updateCartItem"]
        print(f"Updated cart item to 0, items count={len(cart_data['items'])}")
        assert len(cart_data["items"]) == 0

        # Test removeFromCart
        print("\n--- Test Mutation: removeFromCart ---")
        # Add item back first
        await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": prod1["id"], "quantity": 1},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        remove_from_cart_mutation = """
            mutation RemoveFromCart($productId: UUID!) {
                removeFromCart(productId: $productId) {
                    id
                    items {
                        id
                    }
                }
            }
        """
        result = await schema.execute(
            remove_from_cart_mutation,
            variable_values={"productId": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["removeFromCart"]
        print(f"Removed item from cart, items count={len(cart_data['items'])}")
        assert len(cart_data["items"]) == 0

        # Test clearCart
        print("\n--- Test Mutation: clearCart ---")
        # Add item back first
        await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": prod1["id"], "quantity": 1},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        clear_cart_mutation = """
            mutation ClearCart {
                clearCart {
                    id
                    items {
                        id
                    }
                }
            }
        """
        result = await schema.execute(
            clear_cart_mutation,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["clearCart"]
        print(f"Cleared cart, items count={len(cart_data['items'])}")
        assert len(cart_data["items"]) == 0

        # Test Cross-Tenant Guard on addToCart
        print("\n--- Test Cross-Tenant Guard on addToCart ---")
        fake_product_id = str(uuid.uuid4())
        result = await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": fake_product_id, "quantity": 1},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: addToCart failed as expected: {result.errors[0].message}")
            assert "Product not found or belongs to another tenant" in result.errors[0].message
        else:
            raise AssertionError("addToCart should have failed for fake product ID")
        # Re-set selling price for prod1 since it was deleted in previous test blocks
        print("\n--- Resetting selling price for coupons test ---")
        await schema.execute(
            set_price_mutation,
            variable_values={
                "input": {
                    "productId": prod1["id"],
                    "pricingTypeId": pt_selling["id"],
                    "price": 999.99
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )

        # 6r. Test Coupons & Promotions System
        print("\n--- Test Mutation: createCoupon (Admin) ---")
        create_coupon_mutation = """
            mutation CreateCoupon($input: CreateCouponInput!) {
                createCoupon(input: $input) {
                    id
                    code
                    discountType
                    discountValue
                    minOrderValue
                    maxDiscountAmount
                    isActive
                    rules
                }
            }
        """
        # Create FLAT discount coupon
        from datetime import datetime, timedelta
        start_date_str = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        end_date_str = (datetime.utcnow() + timedelta(days=5)).isoformat() + "Z"
        
        result = await schema.execute(
            create_coupon_mutation,
            variable_values={
                "input": {
                    "code": "WELCOME15",
                    "discountType": "FLAT",
                    "discountValue": 15.00,
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "minOrderValue": 20.00,
                    "usageLimitPerUser": 1
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"CreateCoupon Error: {result.errors}")
            return
        coupon_flat = result.data["createCoupon"]
        print(f"Coupon created successfully: {coupon_flat['code']} (ID: {coupon_flat['id']})")
        assert coupon_flat["code"] == "WELCOME15"
        assert coupon_flat["discountType"] == "FLAT"

        # Create Category Restricted PERCENTAGE coupon
        result = await schema.execute(
            create_coupon_mutation,
            variable_values={
                "input": {
                    "code": "VIP20",
                    "discountType": "PERCENTAGE",
                    "discountValue": 20.00,
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "maxDiscountAmount": 10.00,
                    "rules": {
                        "only_categories": [cat_parent["id"]]
                    }
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        coupon_perc = result.data["createCoupon"]
        print(f"Percentage Coupon created successfully: {coupon_perc['code']} (ID: {coupon_perc['id']})")
        assert coupon_perc["rules"]["only_categories"] == [cat_parent["id"]]

        # Fetch Cart and Add prod1 (if empty)
        print("\n--- Add product to cart to test coupons ---")
        # Ensure prod1 is in cart with quantity 2
        await schema.execute(
            add_to_cart_mutation,
            variable_values={"productId": prod1["id"], "quantity": 2},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )

        # Simulate Coupon: WELCOME15
        print("\n--- Test Query: simulateCoupon (FLAT WELCOME15) ---")
        simulate_coupon_query = """
            query SimulateCoupon($code: String!) {
                simulateCoupon(code: $code) {
                    isValid
                    errorMessage
                    discountApplied
                    newTotal
                    originalTotal
                }
            }
        """
        result = await schema.execute(
            simulate_coupon_query,
            variable_values={"code": "welcome15"},  # case-insensitive check
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        sim_data = result.data["simulateCoupon"]
        print(f"Simulation result for WELCOME15: isValid={sim_data['isValid']}, error={sim_data['errorMessage']}, discountApplied={sim_data['discountApplied']}, newTotal={sim_data['newTotal']}")
        assert sim_data["isValid"] is True
        assert sim_data["discountApplied"] == 15.00
        assert sim_data["originalTotal"] > 20.00

        # Simulate Coupon: VIP20 (Category restricted)
        print("\n--- Test Query: simulateCoupon (PERCENTAGE VIP20) ---")
        result = await schema.execute(
            simulate_coupon_query,
            variable_values={"code": "VIP20"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        sim_perc_data = result.data["simulateCoupon"]
        print(f"Simulation result for VIP20: isValid={sim_perc_data['isValid']}, discountApplied={sim_perc_data['discountApplied']}")
        assert sim_perc_data["isValid"] is True
        # Original total is 2 * 999 or something, 20% of 2000 is 400, but capped at 10.00
        assert sim_perc_data["discountApplied"] == 10.00

        # Apply Coupon WELCOME15
        print("\n--- Test Mutation: applyCoupon ---")
        apply_coupon_mutation = """
            mutation ApplyCoupon($code: String!, $orderId: UUID!) {
                applyCoupon(code: $code, orderId: $orderId) {
                    isValid
                    discountApplied
                }
            }
        """
        order_uuid = str(uuid.uuid4())
        result = await schema.execute(
            apply_coupon_mutation,
            variable_values={"code": "WELCOME15", "orderId": order_uuid},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"ApplyCoupon Error: {result.errors}")
            return
        apply_data = result.data["applyCoupon"]
        print(f"Coupon applied: isValid={apply_data['isValid']}, discount={apply_data['discountApplied']}")
        assert apply_data["isValid"] is True
        assert apply_data["discountApplied"] == 15.00

        # Verify usage count incremented
        print("\n--- Test Query: get coupon details and check usageCount ---")
        query_coupon_details = """
            query GetCoupon($code: String!) {
                coupon(code: $code) {
                    code
                    usageCount
                }
            }
        """
        result = await schema.execute(
            query_coupon_details,
            variable_values={"code": "WELCOME15"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        coupon_details = result.data["coupon"]
        print(f"Usage count for WELCOME15: {coupon_details['usageCount']}")
        assert coupon_details["usageCount"] == 1

        # Test limit per user: applying it again should fail
        print("\n--- Test Mutation: applyCoupon again (should fail per-user limit) ---")
        result = await schema.execute(
            apply_coupon_mutation,
            variable_values={"code": "WELCOME15", "orderId": str(uuid.uuid4())},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Success: applyCoupon failed as expected: {result.errors[0].message}")
            assert "already reached the redemption limit" in result.errors[0].message
        else:
            raise AssertionError("applyCoupon should have failed because of per-user limit")

        # --- NEW CART COUPONS, DELIVERY QUOTES & BILL SUMMARY TESTS ---
        print("\n--- Test Mutation: create cart coupons (CARTWELCOME & CARTPERCENT) ---")
        # Let's create CARTWELCOME coupon
        result = await schema.execute(
            create_coupon_mutation,
            variable_values={
                "input": {
                    "code": "CARTWELCOME",
                    "discountType": "FLAT",
                    "discountValue": 15.00,
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "minOrderValue": 20.00,
                    "usageLimitPerUser": 2
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        
        # Let's create CARTPERCENT coupon
        result = await schema.execute(
            create_coupon_mutation,
            variable_values={
                "input": {
                    "code": "CARTPERCENT",
                    "discountType": "PERCENTAGE",
                    "discountValue": 20.00,
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "usageLimitPerUser": 2
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors

        print("\n--- Test Query: get cart with billSummary (empty coupons/delivery) ---")
        get_cart_query = """
            query {
                myCart {
                    id
                    deliveryFee
                    deliveryService
                    estimatedDays
                    appliedCoupons {
                        code
                    }
                    billSummary {
                        itemTotal
                        discountApplied
                        deliveryFee
                        tax
                        grandTotal
                    }
                }
            }
        """
        result = await schema.execute(
            get_cart_query,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["myCart"]
        summary = cart_data["billSummary"]
        print(f"Empty cart summary: {summary}")
        # prod1 in cart with quantity 2. Price of prod1 is 999.99 => itemTotal = 1999.98
        assert summary["itemTotal"] == 1999.98
        assert summary["discountApplied"] == 0.00
        assert summary["deliveryFee"] == 0.00
        # tax: 5% of 1999.98 = 99.999 => 100.00
        assert summary["tax"] == 100.00
        assert summary["grandTotal"] == 2099.98

        print("\n--- Test Mutation: applyCouponToCart (allow_multiple_coupons=False) ---")
        apply_coupon_to_cart_mutation = """
            mutation ApplyCouponToCart($code: String!) {
                applyCouponToCart(code: $code) {
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
        """
        # Apply CARTWELCOME
        result = await schema.execute(
            apply_coupon_to_cart_mutation,
            variable_values={"code": "CARTWELCOME"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["applyCouponToCart"]
        assert len(cart_data["appliedCoupons"]) == 1
        assert cart_data["appliedCoupons"][0]["code"] == "CARTWELCOME"
        assert cart_data["billSummary"]["discountApplied"] == 15.00

        # Since allow_multiple_coupons=False, applying CARTPERCENT should REPLACE CARTWELCOME
        result = await schema.execute(
            apply_coupon_to_cart_mutation,
            variable_values={"code": "CARTPERCENT"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["applyCouponToCart"]
        assert len(cart_data["appliedCoupons"]) == 1
        assert cart_data["appliedCoupons"][0]["code"] == "CARTPERCENT"
        # 20% of 1999.98 = 399.996 => 400.00
        assert cart_data["billSummary"]["discountApplied"] == 400.00

        print("\n--- Test Mutation: allow_multiple_coupons = True & apply multiple ---")
        # Toggle tenant settings to allow multiple coupons
        tenant = await db.get(Tenant, tenant_id)
        tenant.allow_multiple_coupons = True
        await db.commit()

        # Clear coupons first
        clear_coupons_mutation = """
            mutation {
                clearCouponsFromCart {
                    appliedCoupons {
                        code
                    }
                    billSummary {
                        discountApplied
                    }
                }
            }
        """
        result = await schema.execute(
            clear_coupons_mutation,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["clearCouponsFromCart"]["appliedCoupons"]) == 0

        # Now apply CARTWELCOME
        result = await schema.execute(
            apply_coupon_to_cart_mutation,
            variable_values={"code": "CARTWELCOME"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors

        # And apply CARTPERCENT (should stack/append sequentially)
        result = await schema.execute(
            apply_coupon_to_cart_mutation,
            variable_values={"code": "CARTPERCENT"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["applyCouponToCart"]
        applied_codes = [c["code"] for c in cart_data["appliedCoupons"]]
        assert "CARTWELCOME" in applied_codes
        assert "CARTPERCENT" in applied_codes
        assert len(applied_codes) == 2

        # Verify sequential discount calculation:
        # subtotal = 1999.98
        # CARTWELCOME discount = 15.00 => remaining = 1984.98
        # CARTPERCENT discount = 20% of 1984.98 = 396.996 => 397.00
        # total discount = 15.00 + 397.00 = 412.00
        assert cart_data["billSummary"]["discountApplied"] == 412.00

        print("\n--- Test Mutation: removeCouponFromCart ---")
        remove_coupon_mutation = """
            mutation RemoveCoupon($code: String!) {
                removeCouponFromCart(code: $code) {
                    appliedCoupons {
                        code
                    }
                    billSummary {
                        discountApplied
                    }
                }
            }
        """
        result = await schema.execute(
            remove_coupon_mutation,
            variable_values={"code": "CARTWELCOME"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["removeCouponFromCart"]
        assert len(cart_data["appliedCoupons"]) == 1
        assert cart_data["appliedCoupons"][0]["code"] == "CARTPERCENT"
        assert cart_data["billSummary"]["discountApplied"] == 400.00

        print("\n--- Test Delivery Quoting & Selection ---")
        from app.users.models import UserAddress
        stmt_addr = select(UserAddress).where(UserAddress.user_id == db_user.id)
        res_addr = await db.execute(stmt_addr)
        db_addr = res_addr.scalars().first()
        assert db_addr is not None
        addr_id_str = str(db_addr.id)

        # Query quotes
        query_quotes = """
            query GetQuotes($addressId: UUID!) {
                deliveryQuotes(addressId: $addressId) {
                    serviceName
                    deliveryFee
                    estimatedDays
                }
            }
        """
        result = await schema.execute(
            query_quotes,
            variable_values={"addressId": addr_id_str},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        quotes = result.data["deliveryQuotes"]
        assert len(quotes) == 2
        services = [q["serviceName"] for q in quotes]
        assert "Standard" in services
        assert "Express" in services

        # Select standard option
        select_delivery_mutation = """
            mutation SelectDelivery($addressId: UUID!, $serviceName: String!) {
                selectDeliveryOption(addressId: $addressId, serviceName: $serviceName) {
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
        """
        result = await schema.execute(
            select_delivery_mutation,
            variable_values={"addressId": addr_id_str, "serviceName": "Standard"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        cart_data = result.data["selectDeliveryOption"]
        assert cart_data["deliveryService"] == "Standard"
        assert cart_data["deliveryFee"] > 0
        assert cart_data["billSummary"]["deliveryFee"] == cart_data["deliveryFee"]

        # --- NEW ORDERS, MULTIPLE PAYMENTS & RETURNS INTEGRATION TESTS ---
        print("\n--- Test Mutation: checkoutCart ---")
        checkout_mutation = """
            mutation CheckoutCart($paymentMethod: String!) {
                checkoutCart(paymentMethod: $paymentMethod) {
                    id
                    orderStatus
                    paymentStatus
                    appliedCoupons
                    deliveryService
                    deliveryFee
                    itemTotal
                    discountApplied
                    tax
                    grandTotal
                    items {
                        id
                        productId
                        quantity
                        unitPrice
                        discountApplied
                        subtotal
                    }
                }
            }
        """
        result = await schema.execute(
            checkout_mutation,
            variable_values={"paymentMethod": "WALLET"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        order_data = result.data["checkoutCart"]
        order_id = order_data["id"]
        assert order_data["orderStatus"] == "PENDING"
        assert order_data["paymentStatus"] == "UNPAID"
        assert len(order_data["items"]) == 1
        
        item = order_data["items"][0]
        assert order_data["itemTotal"] == 1999.98
        assert order_data["discountApplied"] == 400.00
        assert order_data["deliveryFee"] == 120.00
        assert order_data["tax"] == 86.00
        assert order_data["grandTotal"] == 1805.98
        
        assert item["quantity"] == 2
        assert item["unitPrice"] == 999.99
        assert item["discountApplied"] == 400.00
        assert item["subtotal"] == 1599.98

        # Verify that the cart items are now cleared
        print("\n--- Verify cart is cleared after checkout ---")
        result = await schema.execute(
            get_cart_query,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["myCart"]["appliedCoupons"]) == 0
        
        # Verify database coupon usage count was incremented
        print("\n--- Verify coupon usage count incremented ---")
        result = await schema.execute(
            query_coupon_details,
            variable_values={"code": "CARTPERCENT"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert result.data["coupon"]["usageCount"] == 1

        print("\n--- Test Mutation: recordPayment (Split Payment 1 - Partial) ---")
        record_payment_mutation = """
            mutation RecordPayment($orderId: UUID!, $amount: Float!, $paymentMethod: String!, $status: String!) {
                recordPayment(orderId: $orderId, amount: $amount, paymentMethod: $paymentMethod, status: $status) {
                    id
                    amount
                    status
                    paymentMethod
                }
            }
        """
        result = await schema.execute(
            record_payment_mutation,
            variable_values={"orderId": order_id, "amount": 100.00, "paymentMethod": "WALLET", "status": "COMPLETED"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        
        # Verify order paymentStatus is PARTIALLY_PAID
        result = await schema.execute(
            """
            query GetOrder($id: UUID!) {
                order(id: $id) {
                    paymentStatus
                    payments {
                        amount
                        status
                        paymentMethod
                    }
                }
            }
            """,
            variable_values={"id": order_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["order"]["paymentStatus"] == "PARTIALLY_PAID"
        assert len(result.data["order"]["payments"]) == 1

        print("\n--- Test Mutation: recordPayment (Split Payment 2 - Complete) ---")
        result = await schema.execute(
            record_payment_mutation,
            variable_values={"orderId": order_id, "amount": 1705.98, "paymentMethod": "CARD", "status": "COMPLETED"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        
        # Verify order paymentStatus is PAID
        result = await schema.execute(
            """
            query GetOrder($id: UUID!) {
                order(id: $id) {
                    paymentStatus
                    payments {
                        amount
                    }
                }
            }
            """,
            variable_values={"id": order_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["order"]["paymentStatus"] == "PAID"
        assert len(result.data["order"]["payments"]) == 2

        print("\n--- Test Mutation: requestOrderReturn ---")
        request_return_mutation = """
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
        """
        order_item_id = item["id"]
        result = await schema.execute(
            request_return_mutation,
            variable_values={
                "input": {
                    "orderId": order_id,
                    "reason": "Wrong item delivered",
                    "items": [
                        {
                            "orderItemId": order_item_id,
                            "quantity": 1,
                            "condition": "UNOPENED"
                        }
                    ]
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        return_data = result.data["requestOrderReturn"]
        return_id = return_data["id"]
        assert return_data["status"] == "PENDING_APPROVAL"
        assert return_data["refundStatus"] == "PENDING"
        assert return_data["items"][0]["quantity"] == 1

        print("\n--- Test Mutation: approveOrderReturn (Admin) ---")
        approve_return_mutation = """
            mutation ApproveReturn($returnId: UUID!, $approved: Boolean!) {
                approveOrderReturn(returnId: $returnId, approved: $approved) {
                    status
                    refundStatus
                }
            }
        """
        result = await schema.execute(
            approve_return_mutation,
            variable_values={"returnId": return_id, "approved": True},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["approveOrderReturn"]["status"] == "APPROVED"

        print("\n--- Test Mutation: completeOrderReturn (Admin) ---")
        complete_return_mutation = """
            mutation CompleteReturn($returnId: UUID!, $refundAmount: Float!) {
                completeOrderReturn(returnId: $returnId, refundAmount: $refundAmount) {
                    status
                    refundStatus
                    refundAmount
                }
            }
        """
        result = await schema.execute(
            complete_return_mutation,
            variable_values={"returnId": return_id, "refundAmount": 799.99},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["completeOrderReturn"]["status"] == "COMPLETED"
        assert result.data["completeOrderReturn"]["refundStatus"] == "REFUNDED"
        assert result.data["completeOrderReturn"]["refundAmount"] == 799.99

        # Verify order's orderStatus is PARTIALLY_RETURNED
        result = await schema.execute(
            """
            query GetOrderDetails($id: UUID!) {
                order(id: $id) {
                    orderStatus
                    payments {
                        amount
                        status
                        paymentMethod
                    }
                }
            }
            """,
            variable_values={"id": order_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["order"]["orderStatus"] == "PARTIALLY_RETURNED"
        payments = result.data["order"]["payments"]
        assert len(payments) == 3
        refund_entry = [p for p in payments if p["paymentMethod"] == "REFUND"][0]
        assert refund_entry["amount"] == -799.99
        assert refund_entry["status"] == "REFUNDED"

        print("\n--- Delaying order cleanup until after reviews/loyalty tests ---")

        # Clear cart to clean up
        await schema.execute(
            clear_cart_mutation,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )

        # --- Start of Loyalty, Inventory, & Reviews integration tests ---
        print("\n--- Test Mutation: updateProductStock (Admin) ---")
        update_stock_mutation = """
            mutation UpdateStock($productId: UUID!, $stock: Int!) {
                updateProductStock(productId: $productId, stock: $stock) {
                    stock
                }
            }
        """
        result = await schema.execute(
            update_stock_mutation,
            variable_values={"productId": prod1["id"], "stock": 10},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["updateProductStock"]["stock"] == 10

        print("\n--- Test Query: product stock resolving ---")
        query_prod_stock = """
            query GetProductStock($id: UUID!) {
                product(id: $id) {
                    stock
                }
            }
        """
        result = await schema.execute(
            query_prod_stock,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["product"]["stock"] == 10

        # Specialized Reviews Tests (Product, Order, Company)
        print("\n--- Test Mutation: createProductReview ---")
        create_prod_review_mutation = """
            mutation CreateProdReview($input: CreateProductReviewInput!) {
                createProductReview(input: $input) {
                    id
                    ratingPoints
                    review
                    status
                }
            }
        """
        result = await schema.execute(
            create_prod_review_mutation,
            variable_values={"input": {"productId": prod1["id"], "ratingPoints": 5, "review": "Excellent product!"}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        prod_review_id = result.data["createProductReview"]["id"]
        assert result.data["createProductReview"]["status"] == "PENDING"

        print("\n--- Test Mutation: createOrderReview ---")
        create_order_review_mutation = """
            mutation CreateOrderReview($input: CreateOrderReviewInput!) {
                createOrderReview(input: $input) {
                    id
                    ratingPoints
                    review
                    status
                }
            }
        """
        result = await schema.execute(
            create_order_review_mutation,
            variable_values={"input": {"orderId": order_id, "ratingPoints": 4, "review": "Order was fast."}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        order_review_id = result.data["createOrderReview"]["id"]
        assert result.data["createOrderReview"]["status"] == "PENDING"

        print("\n--- Test Mutation: createCompanyReview ---")
        create_company_review_mutation = """
            mutation CreateCompanyReview($input: CreateCompanyReviewInput!) {
                createCompanyReview(input: $input) {
                    id
                    ratingPoints
                    review
                    status
                }
            }
        """
        result = await schema.execute(
            create_company_review_mutation,
            variable_values={"input": {"tenantId": str(tenant_id), "ratingPoints": 5, "review": "DreamCorp is awesome."}},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        company_review_id = result.data["createCompanyReview"]["id"]
        assert result.data["createCompanyReview"]["status"] == "PENDING"

        # Check pending queries
        print("\n--- Test Queries: Approved reviews (should all be empty initially) ---")
        result = await schema.execute(
            "query($productId: UUID!) { productReviews(productId: $productId) { id } }",
            variable_values={"productId": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["productReviews"]) == 0

        # Check admin moderation queries
        print("\n--- Test Queries: Admin moderation queries ---")
        result = await schema.execute(
            "query { adminProductReviews { id status } }",
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert any(r["id"] == prod_review_id for r in result.data["adminProductReviews"])

        result = await schema.execute(
            "query { adminOrderReviews { id status } }",
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert any(r["id"] == order_review_id for r in result.data["adminOrderReviews"])

        result = await schema.execute(
            "query { adminCompanyReviews { id status } }",
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert any(r["id"] == company_review_id for r in result.data["adminCompanyReviews"])

        # Approve all 3
        print("\n--- Test Mutations: Approve all reviews ---")
        result = await schema.execute(
            "mutation($id: UUID!) { updateProductReviewStatus(id: $id, status: \"APPROVED\") { status } }",
            variable_values={"id": prod_review_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["updateProductReviewStatus"]["status"] == "APPROVED"

        result = await schema.execute(
            "mutation($id: UUID!) { updateOrderReviewStatus(id: $id, status: \"APPROVED\") { status } }",
            variable_values={"id": order_review_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["updateOrderReviewStatus"]["status"] == "APPROVED"

        result = await schema.execute(
            "mutation($id: UUID!) { updateCompanyReviewStatus(id: $id, status: \"APPROVED\") { status } }",
            variable_values={"id": company_review_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["updateCompanyReviewStatus"]["status"] == "APPROVED"

        # Verify approved reviews are returned now
        print("\n--- Test Queries: Approved reviews (should now contain approved items) ---")
        query_prod_reviews = """
            query GetProductReviews($id: UUID!) {
                product(id: $id) {
                    reviews {
                        id
                    }
                }
            }
        """
        result = await schema.execute(
            query_prod_reviews,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["product"]["reviews"]) == 1
        prod_review_id = result.data["product"]["reviews"][0]["id"]

        result = await schema.execute(
            "query($orderId: UUID!) { orderReviews(orderId: $orderId) { id } }",
            variable_values={"orderId": order_id},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["orderReviews"]) == 1

        result = await schema.execute(
            "query($tenantId: UUID!) { companyReviews(tenantId: $tenantId) { id } }",
            variable_values={"tenantId": str(tenant_id)},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert len(result.data["companyReviews"]) == 1

        # Wallet Tests
        print("\n--- Test Query: myWallet (Initial) ---")
        query_my_wallet = """
            query {
                myWallet {
                    points
                    transactions {
                        id
                    }
                }
            }
        """
        result = await schema.execute(
            query_my_wallet,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["myWallet"]["points"] == 0.0

        print("\n--- Test Mutation: creditWallet ---")
        credit_wallet_mutation = """
            mutation CreditWallet($userId: UUID!, $points: Float!, $remarks: String) {
                creditWallet(userId: $userId, points: $points, remarks: $remarks) {
                    id
                    points
                    type
                }
            }
        """
        result = await schema.execute(
            credit_wallet_mutation,
            variable_values={"userId": str(db_user.id), "points": 150.0, "remarks": "Welcome Bonus"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["creditWallet"]["points"] == 150.0
        assert result.data["creditWallet"]["type"] == "CREDIT"

        result = await schema.execute(
            query_my_wallet,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["myWallet"]["points"] == 150.0
        assert len(result.data["myWallet"]["transactions"]) == 1

        print("\n--- Test Mutation: debitWallet ---")
        debit_wallet_mutation = """
            mutation DebitWallet($userId: UUID!, $points: Float!, $remarks: String) {
                debitWallet(userId: $userId, points: $points, remarks: $remarks) {
                    id
                    points
                    type
                }
            }
        """
        result = await schema.execute(
            debit_wallet_mutation,
            variable_values={"userId": str(db_user.id), "points": 50.0, "remarks": "Purchase Redemption"},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["debitWallet"]["points"] == 50.0
        assert result.data["debitWallet"]["type"] == "DEBIT"

        result = await schema.execute(
            query_my_wallet,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["myWallet"]["points"] == 100.0

        # Referral Tests
        print("\n--- Test Mutation: generateReferralCode ---")
        gen_ref_mutation = """
            mutation GenRef($code: String) {
                generateReferralCode(customCode: $code) {
                    referralCode
                    referralPoints
                }
            }
        """
        ref_code = f"TESTREF{rand_id}".upper()
        result = await schema.execute(
            gen_ref_mutation,
            variable_values={"code": ref_code},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["generateReferralCode"]["referralCode"] == ref_code
        assert result.data["generateReferralCode"]["referralPoints"] == 0.0

        print("\n--- Creating referred user to claim referral ---")
        db_user2 = User(
            tenant_id=tenant_id,
            name="Referred User",
            mobilenumber=f"900000{rand_id}",
            email=f"referred_{rand_id}@dreamcorp.com",
            role="USER",
            status="ACTIVE"
        )
        db.add(db_user2)
        await db.commit()

        print("\n--- Test Mutation: claimReferral ---")
        claim_ref_mutation = """
            mutation ClaimRef($input: ClaimReferralInput!) {
                claimReferral(input: $input) {
                    id
                    points
                    referredEntity
                }
            }
        """
        claim_input = {
            "referrerCode": ref_code,
            "referredEntity": "USER",
            "referredEntityId": str(db_user2.id),
            "points": 50.0,
            "remarks": "Successful sign-up referral"
        }
        result = await schema.execute(
            claim_ref_mutation,
            variable_values={"input": claim_input},
            context_value=make_context(user=db_user2, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["claimReferral"]["points"] == 50.0
        assert result.data["claimReferral"]["referredEntity"] == "USER"

        print("\n--- Verify referrer wallet points balance increased ---")
        result = await schema.execute(
            query_my_wallet,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["myWallet"]["points"] == 150.0  # 100.0 + 50.0 referral credit

        print("\n--- Verify referrer myReferral query ---")
        query_my_referral = """
            query {
                myReferral {
                    referralCode
                    referralPoints
                    histories {
                        id
                        points
                        referredEntity
                    }
                }
            }
        """
        result = await schema.execute(
            query_my_referral,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        ref_info = result.data["myReferral"]
        assert ref_info["referralCode"] == ref_code
        assert ref_info["referralPoints"] == 50.0
        assert len(ref_info["histories"]) == 1
        assert ref_info["histories"][0]["points"] == 50.0

        # Clean up reviews, orders, and stock records so that the subsequent product deletion test can succeed without violating foreign key constraints
        print("\n--- Cleaning up review, order, and stock records for subsequent test compatibility ---")
        from sqlalchemy import delete
        from app.reviews.models import ProductReview, OrderReview, CompanyReview
        from app.products.products.models import ProductStock
        from app.orders.models import Order, OrderReturn, OrderReturnItem, OrderPayment
        await db.execute(delete(ProductReview))
        await db.execute(delete(OrderReview))
        await db.execute(delete(CompanyReview))
        await db.execute(delete(OrderReturnItem))
        await db.execute(delete(OrderReturn))
        await db.execute(delete(OrderPayment))
        await db.execute(delete(Order))
        await db.execute(delete(ProductStock))
        await db.commit()
        # --- End of Loyalty, Inventory, & Reviews integration tests ---

        # 6p. Test Mutation: deleteProduct
        print("\n--- Test Mutation: deleteProduct ---")
        delete_product_mutation = """
            mutation DeleteProduct($id: UUID!) {
                deleteProduct(id: $id)
            }
        """
        result = await schema.execute(
            delete_product_mutation,
            variable_values={"id": prod1["id"]},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )

        # Verify product 1 is gone and cascade deleted product 2 (child)
        result = await schema.execute(
            query_products,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        products_after_delete = result.data["products"]
        print(f"Products remaining in DB: {len(products_after_delete)}")
        assert not any(p["id"] in [prod1["id"], prod2["id"]] for p in products_after_delete), "Products should be deleted"

        # 7. Test Query me (Unauthorized check)
        print("\n--- Test Query: me (Unauthorized check) ---")
        result = await schema.execute(
            query_me,
            context_value=make_context(user=None)
        )
        
        if result.errors:
            print(f"Success: Query failed as expected (UnauthorizedError): {result.errors[0].message}")
        else:
            print("Failure: Query me succeeded without authorization headers!")

    # Close database client connections
    await redis_client.close()
    if mongo_client:
        mongo_client.close()
    
    print("\n=== INTEGRATION TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
