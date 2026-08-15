import asyncio
import uuid
import sys
import os
import json
import hmac
import hashlib
from decimal import Decimal
import httpx

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphql.schema import schema
from app.graphql.context import GraphQLContext
from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.database.redis import redis_client
from app.users.models import User
from app.orders.models import Order, OrderPayment
from app.payments.models import PaymentGateway, TenantPaymentGateway, TenantCommission
from app.main import app

rand_id = uuid.uuid4().hex[:6]
TEST_BUSINESS_NAME = f"PayCorp {rand_id}"
TEST_ADMIN_EMAIL = f"admin_{rand_id}@paycorp.com"
TEST_ADMIN_MOBILE = f"991122{rand_id}"
TEST_ADMIN_PASSWORD = "AdminPassword123!"

async def run_payments_integration_test():
    print("=== STARTING PLUGGABLE PAYMENTS INTEGRATION TEST ===")
    
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
        print("\n--- Setup Tenant & Admin ---")
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
                "adminName": "Payment Admin",
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

        # Fetch admin user model
        from sqlalchemy.future import select
        stmt = select(User).where((User.tenant_id == tenant_id) & (User.email == TEST_ADMIN_EMAIL))
        res = await db.execute(stmt)
        db_user = res.scalar_one_or_none()
        assert db_user is not None, "Admin user should exist in DB"
        print(f"Admin User ID: {db_user.id}")

        # Promote user to SUPER_ADMIN to test platform-level endpoints as well
        db_user.role = "SUPER_ADMIN"
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # 3. Create platform-level PaymentGateway RAZORPAY
        print("\n--- Test Scenario 1: Configure Platform Payment Gateway ---")
        configure_pg_mutation = """
            mutation ConfigurePlatformGateway($input: ConfigurePlatformGatewayInput!) {
                configurePlatformGateway(input: $input) {
                    id
                    name
                    isActive
                }
            }
        """
        result = await schema.execute(
            configure_pg_mutation,
            variable_values={
                "input": {
                    "name": "RAZORPAY",
                    "credentials": {"key_id": "mock_platform_key", "key_secret": "mock_platform_secret"},
                    "webhookSecret": "platform_secret",
                    "isActive": True
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"ConfigurePlatformGateway error: {result.errors}"
        platform_gw_id = uuid.UUID(result.data["configurePlatformGateway"]["id"])
        print(f"Platform gateway configured: {platform_gw_id}")

        # 4. Create Tenant-level config
        print("\n--- Test Scenario 2: Configure Tenant Payment Gateway ---")
        configure_tg_mutation = """
            mutation ConfigureTenantGateway($input: ConfigureTenantGatewayInput!) {
                configureTenantGateway(input: $input) {
                    id
                    isActive
                }
            }
        """
        result = await schema.execute(
            configure_tg_mutation,
            variable_values={
                "input": {
                    "gatewayId": str(platform_gw_id),
                    "credentials": {"key_id": "mock_tenant_key", "key_secret": "mock_tenant_secret"},
                    "webhookSecret": "tenant_secret",
                    "isActive": True
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"ConfigureTenantGateway error: {result.errors}"
        tenant_gw_id = uuid.UUID(result.data["configureTenantGateway"]["id"])
        print(f"Tenant gateway configured: {tenant_gw_id}")

        # 5. Create Order directly to test payment flows
        print("\n--- Test Scenario 3: Create Order and Initiate Direct Tenant Payment ---")
        order_direct = Order(
            tenant_id=tenant_id,
            user_id=db_user.id,
            item_total=Decimal("150.00"),
            grand_total=Decimal("150.00"),
            order_status="PENDING",
            payment_status="UNPAID"
        )
        db.add(order_direct)
        await db.commit()
        await db.refresh(order_direct)
        print(f"Order created for direct flow: {order_direct.id}")

        initiate_payment_mutation = """
            mutation InitiateOnlinePayment($orderId: UUID!) {
                initiateOnlinePayment(orderId: $orderId) {
                    key
                    amount
                    currency
                    orderId
                    paymentId
                }
            }
        """
        result = await schema.execute(
            initiate_payment_mutation,
            variable_values={"orderId": str(order_direct.id)},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"InitiateOnlinePayment error: {result.errors}"
        payment_details = result.data["initiateOnlinePayment"]
        assert payment_details["key"] == "mock_tenant_key", f"Expected mock_tenant_key, got {payment_details['key']}"
        assert payment_details["amount"] == 15000, f"Expected 15000 paise, got {payment_details['amount']}"
        rzp_order_id_direct = payment_details["orderId"]
        print(f"Payment initiated. Razorpay Order ID: {rzp_order_id_direct}")

        # Verify OrderPayment gateway field is "RAZORPAY"
        stmt_op = select(OrderPayment).where(OrderPayment.transaction_reference == rzp_order_id_direct)
        res_op = await db.execute(stmt_op)
        op_direct = res_op.scalar_one_or_none()
        assert op_direct is not None
        assert op_direct.gateway == "RAZORPAY", f"Expected gateway RAZORPAY, got {op_direct.gateway}"
        print("Direct payment gateway correctly set to RAZORPAY")

        # Test Webhook for direct payment
        print("\n--- Test Scenario 4: Direct Tenant Webhook Callback ---")
        webhook_payload_direct = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_tenant_12345",
                        "order_id": rzp_order_id_direct,
                        "amount": 15000,
                        "status": "captured"
                    }
                }
            }
        }
        
        # Calculate signature
        payload_bytes = json.dumps(webhook_payload_direct).encode("utf-8")
        computed_sig_direct = hmac.new(
            b"tenant_secret",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        # Execute endpoint via httpx TestClient client
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/webhooks/payments/{tenant_id}/razorpay",
                content=payload_bytes,
                headers={"X-Razorpay-Signature": computed_sig_direct, "Content-Type": "application/json"}
            )
            assert resp.status_code == 200, f"Webhook response status: {resp.status_code} - {resp.text}"
            assert resp.json()["status"] == "processed"

        # Check Order and Payment Status
        await db.refresh(order_direct)
        await db.refresh(op_direct)
        assert op_direct.status == "COMPLETED"
        assert order_direct.payment_status == "PAID", f"Expected Order status PAID, got {order_direct.payment_status}"
        print("Webhook successfully processed! Order set to PAID, Payment set to COMPLETED.")

        # 6. Test Fallback Routing
        print("\n--- Test Scenario 5: Configure Fallback Routing (Gubera Platform Mode) ---")
        
        # Deactivate Tenant gateway
        configure_tg_mutation_deact = """
            mutation ConfigureTenantGateway($input: ConfigureTenantGatewayInput!) {
                configureTenantGateway(input: $input) {
                    id
                    isActive
                }
            }
        """
        result = await schema.execute(
            configure_tg_mutation_deact,
            variable_values={
                "input": {
                    "gatewayId": str(platform_gw_id),
                    "credentials": {"key_id": "mock_tenant_key", "key_secret": "mock_tenant_secret"},
                    "webhookSecret": "tenant_secret",
                    "isActive": False
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors
        assert result.data["configureTenantGateway"]["isActive"] == False
        
        # Set up tenant commission config (5.0% commission, linked account)
        configure_comm_mutation = """
            mutation ConfigureTenantCommission($input: ConfigureTenantCommissionInput!) {
                configureTenantCommission(input: $input) {
                    commissionPercent
                    linkedAccountId
                }
            }
        """
        result = await schema.execute(
            configure_comm_mutation,
            variable_values={
                "input": {
                    "commissionPercent": 5.0,
                    "linkedAccountId": "acc_linked_tenant_xyz"
                }
            },
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"ConfigureTenantCommission error: {result.errors}"
        assert result.data["configureTenantCommission"]["commissionPercent"] == 5.0
        print("Tenant commission configured at 5% with account acc_linked_tenant_xyz")

        # Create new Order for fallback test
        order_fallback = Order(
            tenant_id=tenant_id,
            user_id=db_user.id,
            item_total=Decimal("200.00"),
            grand_total=Decimal("200.00"),
            order_status="PENDING",
            payment_status="UNPAID"
        )
        db.add(order_fallback)
        await db.commit()
        await db.refresh(order_fallback)
        print(f"Order created for fallback flow: {order_fallback.id}")

        # Initiate fallback payment
        result = await schema.execute(
            initiate_payment_mutation,
            variable_values={"orderId": str(order_fallback.id)},
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"InitiateOnlinePayment error: {result.errors}"
        payment_details_fb = result.data["initiateOnlinePayment"]
        assert payment_details_fb["key"] == "mock_platform_key", f"Expected mock_platform_key, got {payment_details_fb['key']}"
        assert payment_details_fb["amount"] == 20000, f"Expected 20000 paise, got {payment_details_fb['amount']}"
        rzp_order_id_fb = payment_details_fb["orderId"]
        print(f"Fallback payment initiated. Razorpay Order ID: {rzp_order_id_fb}")

        # Verify OrderPayment gateway field is "GUBERA"
        stmt_op_fb = select(OrderPayment).where(OrderPayment.transaction_reference == rzp_order_id_fb)
        res_op_fb = await db.execute(stmt_op_fb)
        op_fb = res_op_fb.scalar_one_or_none()
        assert op_fb is not None
        assert op_fb.gateway == "GUBERA", f"Expected gateway GUBERA, got {op_fb.gateway}"
        
        # Verify transfer breakdown details:
        # total amount = 200.00 (20000 paise).
        # commission = 5.0% = 10.00 (1000 paise).
        # transfer amount = 190.00 (19000 paise).
        gateway_resp = op_fb.gateway_response
        assert "transfers" in gateway_resp, "Expected transfers array in gateway response"
        transfer_item = gateway_resp["transfers"][0]
        assert transfer_item["account"] == "acc_linked_tenant_xyz"
        assert transfer_item["amount"] == 19000, f"Expected 19000 paise routed, got {transfer_item['amount']}"
        print("Routed amount and commission transfer correctly verified!")

        # Test Webhook for platform routing payment
        print("\n--- Test Scenario 6: Platform Webhook Callback ---")
        webhook_payload_fb = {
            "event": "order.paid",
            "payload": {
                "order": {
                    "entity": {
                        "id": rzp_order_id_fb,
                        "amount": 20000,
                        "status": "paid"
                    }
                }
            }
        }
        
        # Calculate platform signature
        payload_bytes_fb = json.dumps(webhook_payload_fb).encode("utf-8")
        computed_sig_fb = hmac.new(
            b"platform_secret",
            payload_bytes_fb,
            hashlib.sha256
        ).hexdigest()

        # Execute endpoint via httpx TestClient client
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/webhooks/payments/platform/razorpay",
                content=payload_bytes_fb,
                headers={"X-Razorpay-Signature": computed_sig_fb, "Content-Type": "application/json"}
            )
            assert resp.status_code == 200, f"Webhook response status: {resp.status_code} - {resp.text}"
            assert resp.json()["status"] == "processed"

        # Check Order and Payment Status
        await db.refresh(order_fallback)
        await db.refresh(op_fb)
        assert op_fb.status == "COMPLETED"
        assert order_fallback.payment_status == "PAID", f"Expected Order status PAID, got {order_fallback.payment_status}"
        print("Platform Webhook successfully processed! Fallback Order set to PAID, Payment set to COMPLETED.")

        # 7. Test Deferred Cart checkout payment flow
        print("\n--- Test Scenario 7: Create Cart and Initiate Cart Payment ---")
        from app.products.products.models import Product, ProductStock
        from app.products.pricing.models import PricingType, ProductPrice
        from app.users.models import UserCart, CartItem
        from app.payments.models import PendingCartPayment
        
        # Create product
        product = Product(
            tenant_id=tenant_id,
            title="Deferred Cart Test Laptop",
            sku=f"LAPTOP-DEFERRED-{rand_id}",
            product_type="GOODS"
        )
        db.add(product)
        await db.flush()

        # Add ProductStock
        stock = ProductStock(
            tenant_id=tenant_id,
            product_id=product.id,
            stock=10
        )
        db.add(stock)

        # Add Pricing Type
        stmt_pt = select(PricingType).where(PricingType.tenant_id == tenant_id)
        res_pt = await db.execute(stmt_pt)
        pricing_type = res_pt.scalar_one_or_none()
        if not pricing_type:
            pricing_type = PricingType(tenant_id=tenant_id, type="selling_price")
            db.add(pricing_type)
            await db.flush()
            
        # Add ProductPrice
        prod_price = ProductPrice(
            product_id=product.id,
            pricing_type_id=pricing_type.id,
            price=Decimal("100.00")
        )
        db.add(prod_price)

        # Add Cart and CartItem
        cart = UserCart(
            user_id=db_user.id,
            applied_coupons=[]
        )
        db.add(cart)
        await db.flush()

        cart_item = CartItem(
            cart_id=cart.id,
            user_id=db_user.id,
            product_id=product.id,
            quantity=2
        )
        db.add(cart_item)
        await db.commit()

        # Execute initiateCartPayment
        initiate_cart_payment_mutation = """
            mutation InitiateCartPayment {
                initiateCartPayment {
                    key
                    amount
                    currency
                    orderId
                    paymentId
                }
            }
        """
        result = await schema.execute(
            initiate_cart_payment_mutation,
            context_value=make_context(user=db_user, tenant_id=tenant_id)
        )
        assert not result.errors, f"InitiateCartPayment error: {result.errors}"
        cart_payment_details = result.data["initiateCartPayment"]
        assert cart_payment_details["key"] == "mock_platform_key", f"Expected mock_platform_key, got {cart_payment_details['key']}"
        # grand total = (100.00 * 2) * 1.05 = 210.00 -> 21000 paise
        assert cart_payment_details["amount"] == 21000, f"Expected 21000 paise, got {cart_payment_details['amount']}"
        rzp_order_id_cart = cart_payment_details["orderId"]
        print(f"Cart payment initiated. Razorpay Order ID: {rzp_order_id_cart}")

        # Verify PendingCartPayment details in database
        stmt_pcp = select(PendingCartPayment).where(PendingCartPayment.gateway_order_id == rzp_order_id_cart)
        res_pcp = await db.execute(stmt_pcp)
        pcp_record = res_pcp.scalar_one_or_none()
        assert pcp_record is not None
        assert pcp_record.amount == Decimal("210.00")
        assert len(pcp_record.cart_items) == 1
        assert pcp_record.cart_items[0]["quantity"] == 2
        assert pcp_record.cart_items[0]["unit_price"] == 100.0
        print("PendingCartPayment constraints verified.")

        # Test Webhook Callback for deferred Cart checkout
        print("\n--- Test Scenario 8: Deferred Cart Checkout Webhook Callback ---")
        webhook_payload_cart = {
            "event": "order.paid",
            "payload": {
                "order": {
                    "entity": {
                        "id": rzp_order_id_cart,
                        "amount": 21000,
                        "status": "paid"
                    }
                }
            }
        }
        
        # Calculate platform signature
        payload_bytes_cart = json.dumps(webhook_payload_cart).encode("utf-8")
        computed_sig_cart = hmac.new(
            b"platform_secret",
            payload_bytes_cart,
            hashlib.sha256
        ).hexdigest()

        # Execute webhook endpoint via ASGITransport client
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/webhooks/payments/platform/razorpay",
                content=payload_bytes_cart,
                headers={"X-Razorpay-Signature": computed_sig_cart, "Content-Type": "application/json"}
            )
            assert resp.status_code == 200, f"Webhook response status: {resp.status_code} - {resp.text}"
            assert resp.json()["status"] == "processed"

        # Check Order and Payment Status in Postgres
        stmt_order_created = select(Order).where(
            (Order.tenant_id == tenant_id) & 
            (Order.user_id == db_user.id) &
            (Order.grand_total == Decimal("210.00"))
        )
        res_oc = await db.execute(stmt_order_created)
        order_created = res_oc.scalar_one_or_none()
        assert order_created is not None, "Expected actual Order record to be created in DB via webhook"
        assert order_created.payment_status == "PAID"
        assert order_created.order_status == "PENDING"
        print("Deferred Order created successfully from payment snapshot!")

        # Check OrderPayment status
        stmt_op_created = select(OrderPayment).where(OrderPayment.order_id == order_created.id)
        res_op_c = await db.execute(stmt_op_created)
        op_created = res_op_c.scalar_one_or_none()
        assert op_created is not None
        assert op_created.status == "COMPLETED"
        assert op_created.gateway == "GUBERA"
        print("Completed OrderPayment created successfully!")

        # Check that user's cart is cleared
        stmt_items_cleared = select(CartItem).where(CartItem.cart_id == cart.id)
        res_ic = await db.execute(stmt_items_cleared)
        assert len(res_ic.scalars().all()) == 0, "CartItems should be cleared on checkout"
        print("User shopping cart successfully cleared!")

        # Clean up deferred checkout entities
        await db.delete(op_created)
        await db.delete(order_created)
        await db.delete(pcp_record)
        await db.delete(cart_item)
        await db.delete(cart)
        await db.delete(prod_price)
        await db.delete(stock)
        await db.delete(product)
        await db.commit()

        # Cleanup test data to maintain DB cleanliness
        print("\n--- Cleaning up test configurations and records ---")
        await db.delete(op_direct)
        await db.delete(op_fb)
        await db.delete(order_direct)
        await db.delete(order_fallback)
        
        # Delete configs
        stmt_tc = select(TenantCommission).where(TenantCommission.tenant_id == tenant_id)
        res_tc = await db.execute(stmt_tc)
        tc_item = res_tc.scalar_one_or_none()
        if tc_item:
            await db.delete(tc_item)

        stmt_tg_all = select(TenantPaymentGateway).where(TenantPaymentGateway.tenant_id == tenant_id)
        res_tg_all = await db.execute(stmt_tg_all)
        for tg in res_tg_all.scalars().all():
            await db.delete(tg)

        stmt_pg_all = select(PaymentGateway).where(PaymentGateway.id == platform_gw_id)
        res_pg_all = await db.execute(stmt_pg_all)
        for pg in res_pg_all.scalars().all():
            await db.delete(pg)

        await db.commit()
        print("Database cleanup completed successfully.")

    # Close DB connection
    await redis_client.close()
    if mongo_client:
        mongo_client.close()
        
    print("\n=== PLUGGABLE PAYMENTS INTEGRATION TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_payments_integration_test())
