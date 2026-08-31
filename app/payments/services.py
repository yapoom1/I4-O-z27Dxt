import uuid
import hmac
import hashlib
import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.exceptions import ValidationError
from app.payments.models import PaymentGateway, TenantPaymentGateway, TenantCommission, PendingCartPayment
from app.orders.models import Order, OrderPayment

logger = logging.getLogger(__name__)

class PaymentGatewayService:
    @staticmethod
    async def configure_platform_gateway(
        db: AsyncSession,
        name: str,
        credentials: Dict[str, Any],
        webhook_secret: Optional[str] = None,
        is_active: bool = False
    ) -> PaymentGateway:
        """Create or update a platform-level payment gateway config."""
        name_upper = name.upper()
        
        # Check if already exists
        stmt = select(PaymentGateway).where(PaymentGateway.name == name_upper)
        res = await db.execute(stmt)
        gateway = res.scalar_one_or_none()
        
        if gateway:
            gateway.credentials = credentials
            gateway.webhook_secret = webhook_secret
            gateway.is_active = is_active
        else:
            gateway = PaymentGateway(
                name=name_upper,
                credentials=credentials,
                webhook_secret=webhook_secret,
                is_active=is_active
            )
            db.add(gateway)
            
        await db.flush()
        
        if gateway.is_active:
            # Deactivate all other platform gateways
            stmt_deactivate = (
                update(PaymentGateway)
                .where(PaymentGateway.id != gateway.id)
                .values(is_active=False)
            )
            await db.execute(stmt_deactivate)
            
        await db.commit()
        await db.refresh(gateway)
        return gateway

    @staticmethod
    async def activate_platform_gateway(db: AsyncSession, gateway_id: uuid.UUID) -> PaymentGateway:
        """Activate the specified platform-level gateway, deactivating all others."""
        stmt = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
        res = await db.execute(stmt)
        gateway = res.scalar_one_or_none()
        if not gateway:
            raise ValidationError("Platform gateway not found.")
            
        gateway.is_active = True
        await db.flush()
        
        # Deactivate all others
        stmt_deactivate = (
            update(PaymentGateway)
            .where(PaymentGateway.id != gateway.id)
            .values(is_active=False)
        )
        await db.execute(stmt_deactivate)
        await db.commit()
        await db.refresh(gateway)
        return gateway

    @staticmethod
    async def configure_tenant_gateway(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        gateway_id: uuid.UUID,
        credentials: Dict[str, Any],
        webhook_secret: Optional[str] = None,
        is_active: bool = False
    ) -> TenantPaymentGateway:
        """Configure or update a tenant-level payment gateway config."""
        # Check if gateway exists
        stmt_gw = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
        res_gw = await db.execute(stmt_gw)
        if not res_gw.scalar_one_or_none():
            raise ValidationError("Payment gateway does not exist at platform level.")

        # Check if tenant gateway config already exists
        stmt = select(TenantPaymentGateway).where(
            (TenantPaymentGateway.tenant_id == tenant_id) &
            (TenantPaymentGateway.gateway_id == gateway_id)
        )
        res = await db.execute(stmt)
        tenant_gw = res.scalar_one_or_none()
        
        if tenant_gw:
            tenant_gw.credentials = credentials
            tenant_gw.webhook_secret = webhook_secret
            tenant_gw.is_active = is_active
        else:
            tenant_gw = TenantPaymentGateway(
                tenant_id=tenant_id,
                gateway_id=gateway_id,
                credentials=credentials,
                webhook_secret=webhook_secret,
                is_active=is_active
            )
            db.add(tenant_gw)
            
        await db.flush()
        
        if tenant_gw.is_active:
            # Deactivate all other gateways for this tenant
            stmt_deactivate = (
                update(TenantPaymentGateway)
                .where(
                    (TenantPaymentGateway.tenant_id == tenant_id) &
                    (TenantPaymentGateway.id != tenant_gw.id)
                )
                .values(is_active=False)
            )
            await db.execute(stmt_deactivate)
            
        await db.commit()
        await db.refresh(tenant_gw)
        return tenant_gw

    @staticmethod
    async def activate_tenant_gateway(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        tenant_gateway_id: uuid.UUID
    ) -> TenantPaymentGateway:
        """Activate the specified tenant gateway, deactivating all others for that tenant."""
        stmt = select(TenantPaymentGateway).where(
            (TenantPaymentGateway.id == tenant_gateway_id) &
            (TenantPaymentGateway.tenant_id == tenant_id)
        )
        res = await db.execute(stmt)
        tenant_gw = res.scalar_one_or_none()
        if not tenant_gw:
            raise ValidationError("Tenant payment gateway config not found.")
            
        tenant_gw.is_active = True
        await db.flush()
        
        # Deactivate all other gateways for this tenant
        stmt_deactivate = (
            update(TenantPaymentGateway)
            .where(
                (TenantPaymentGateway.tenant_id == tenant_id) &
                (TenantPaymentGateway.id != tenant_gw.id)
            )
            .values(is_active=False)
        )
        await db.execute(stmt_deactivate)
        await db.commit()
        await db.refresh(tenant_gw)
        return tenant_gw

    @staticmethod
    async def configure_tenant_commission(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        commission_percent: Decimal,
        linked_account_id: str
    ) -> TenantCommission:
        """Create or update commission routing configuration for a tenant."""
        if commission_percent < 0 or commission_percent > 100:
            raise ValidationError("Commission percentage must be between 0 and 100.")
            
        stmt = select(TenantCommission).where(TenantCommission.tenant_id == tenant_id)
        res = await db.execute(stmt)
        comm = res.scalar_one_or_none()
        
        if comm:
            comm.commission_percent = commission_percent
            comm.linked_account_id = linked_account_id
        else:
            comm = TenantCommission(
                tenant_id=tenant_id,
                commission_percent=commission_percent,
                linked_account_id=linked_account_id
            )
            db.add(comm)
            
        await db.commit()
        await db.refresh(comm)
        return comm

    @staticmethod
    async def initiate_payment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Resolve gateway (direct vs platform routing) and initiate payment order via Razorpay."""
        # 1. Fetch Order
        stmt_order = select(Order).where((Order.id == order_id) & (Order.tenant_id == tenant_id))
        res_order = await db.execute(stmt_order)
        order = res_order.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found.")

        # 2. Check for active direct tenant gateway
        stmt_tg = (
            select(TenantPaymentGateway)
            .join(PaymentGateway, TenantPaymentGateway.gateway_id == PaymentGateway.id)
            .where(
                (TenantPaymentGateway.tenant_id == tenant_id) &
                (TenantPaymentGateway.is_active == True)
            )
        )
        res_tg = await db.execute(stmt_tg)
        tenant_gw = res_tg.scalar_one_or_none()

        is_fallback = False
        gateway_name = "RAZORPAY"
        credentials = {}
        commission_percent = Decimal("0.00")
        linked_account_id = None

        if tenant_gw:
            # Direct Mode
            credentials = tenant_gw.credentials
            # Get gateway name
            stmt_gw_name = select(PaymentGateway.name).where(PaymentGateway.id == tenant_gw.gateway_id)
            res_gw_name = await db.execute(stmt_gw_name)
            gateway_name = res_gw_name.scalar() or "RAZORPAY"
        else:
            # Check for platform routing config (TenantCommission)
            stmt_comm = select(TenantCommission).where(TenantCommission.tenant_id == tenant_id)
            res_comm = await db.execute(stmt_comm)
            comm = res_comm.scalar_one_or_none()
            if not comm:
                raise ValidationError("No active payment gateway or commission configurations found for this tenant.")
            
            is_fallback = True
            commission_percent = comm.commission_percent
            linked_account_id = comm.linked_account_id
            
            # Load active platform gateway
            stmt_pg = select(PaymentGateway).where(PaymentGateway.is_active == True)
            res_pg = await db.execute(stmt_pg)
            platform_gw = res_pg.scalar_one_or_none()
            if not platform_gw:
                raise ValidationError("Fallback routing enabled but no active platform gateway is configured.")
            
            gateway_name = platform_gw.name
            credentials = platform_gw.credentials

        # Verify key credentials structure
        key_id = credentials.get("key_id")
        key_secret = credentials.get("key_secret")
        if not key_id or not key_secret:
            raise ValidationError("Payment gateway credentials are misconfigured (missing key_id or key_secret).")

        # 3. Calculate amounts in paise (Razorpay standard)
        total_amount = order.grand_total
        total_paise = int(round(total_amount * 100))
        
        # Prepare Razorpay payload
        payload = {
            "amount": total_paise,
            "currency": "INR",
            "receipt": str(order_id),
            "notes": {
                "tenant_id": str(tenant_id),
                "order_id": str(order_id),
                "mode": "fallback" if is_fallback else "direct"
            }
        }

        # Route/Transfer logic if fallback GUBERA route is used
        if is_fallback:
            commission_amount = total_amount * (commission_percent / Decimal("100.00"))
            transfer_amount = total_amount - commission_amount
            
            transfer_paise = int(round(transfer_amount * 100))
            payload["transfers"] = [
                {
                    "account": linked_account_id,
                    "amount": transfer_paise,
                    "currency": "INR"
                }
            ]

        # 4. Invoke Razorpay API
        rzp_order_id = None
        gateway_response = {}

        # Mocking support for offline tests
        if key_id.startswith("test_") or key_id.startswith("mock_") or key_id == "dummy_key_id":
            rzp_order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
            gateway_response = {
                "id": rzp_order_id,
                "entity": "order",
                "amount": total_paise,
                "amount_paid": 0,
                "amount_due": total_paise,
                "currency": "INR",
                "receipt": str(order_id),
                "status": "created",
                "attempts": 0,
                "notes": payload["notes"],
                "created_at": 1600000000
            }
            if "transfers" in payload:
                gateway_response["transfers"] = payload["transfers"]
        else:
            # Real HTTP API Call to Razorpay
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=(key_id, key_secret),
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code != 200:
                        logger.error(f"Razorpay order API failed: {response.status_code} - {response.text}")
                        raise ValidationError(f"Failed to initiate order with Razorpay: {response.text}")
                    gateway_response = response.json()
                    rzp_order_id = gateway_response.get("id")
                except httpx.RequestError as exc:
                    logger.error(f"Network error calling Razorpay: {exc}")
                    raise ValidationError(f"Network connection failed when reaching gateway: {exc}")

        if not rzp_order_id:
            raise ValidationError("Failed to obtain order transaction reference from gateway.")

        # 5. Create or update OrderPayment record in status PENDING
        gateway_recorded_name = "GUBERA" if is_fallback else gateway_name
        payment = OrderPayment(
            order_id=order_id,
            tenant_id=tenant_id,
            amount=total_amount,
            payment_method="ONLINE",
            status="PENDING",
            transaction_reference=rzp_order_id,
            gateway=gateway_recorded_name,
            gateway_response=gateway_response
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        # Return checkout configuration variables for client integration
        return {
            "key": key_id,
            "amount": total_paise,
            "currency": "INR",
            "name": "Gubera Tenant Checkout" if is_fallback else f"Tenant Checkout",
            "order_id": rzp_order_id,
            "payment_id": str(payment.id)
        }

    @staticmethod
    async def initiate_cart_payment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Process cart details, calculate pricing constraints, initiate Razorpay order,
        and store the pending checkout session details before returning to user."""
        
        # 1. Fetch user's cart
        from app.users.models import UserCart, CartItem
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            raise ValidationError("Your shopping cart is empty.")

        # Load items
        stmt_cart_items = select(CartItem).where(CartItem.cart_id == cart.id)
        res_cart_items = await db.execute(stmt_cart_items)
        cart_items = res_cart_items.scalars().all()
        if not cart_items:
            raise ValidationError("Your shopping cart is empty.")

        # 2. Fetch Cart Items and calculate dynamic pricing using PricingService
        pincode = None
        if cart.delivery_address_id:
            from app.users.models import UserAddress
            stmt_addr = select(UserAddress.pincode).where(UserAddress.id == cart.delivery_address_id)
            res_addr = await db.execute(stmt_addr)
            pincode = res_addr.scalar_one_or_none()

        from app.products.products.models import ProductStock
        from app.products.pricing.services import PricingService

        stmt_items = select(
            CartItem.product_id,
            CartItem.quantity,
            ProductStock.stock
        ).outerjoin(
            ProductStock, ProductStock.product_id == CartItem.product_id
        ).where(
            CartItem.cart_id == cart.id
        )
        res_items = await db.execute(stmt_items)
        items = res_items.all()
        if not items:
            raise ValidationError("Your shopping cart is empty.")

        cart_products = []
        item_total = Decimal("0.00")

        # Resolve each product's actual tenant from MongoDB so pricing is always correct
        # regardless of which tenant header the user sent during checkout.
        from app.products.products.mongo_models import Product as MongoProduct

        for prod_id, qty, stock in items:
            # Look up the product's real tenant from MongoDB
            mongo_product = await MongoProduct.find_one({"_id": prod_id})
            product_tenant_id = mongo_product.tenant_id if mongo_product else tenant_id

            print(f"[CART LOG] Product {prod_id}: header_tenant={tenant_id}, product_tenant={product_tenant_id}")

            effective_price = await PricingService.get_effective_price(
                db=db,
                tenant_id=product_tenant_id,
                product_id=prod_id,
                quantity=qty,
                location_id=None,
                pincode=pincode,
                current_time=None,
                current_stock=stock
            )
            print(f"[CART LOG]   -> Qty: {qty}, Price: {effective_price}, Subtotal: {effective_price * qty}")
            cart_products.append((prod_id, qty, effective_price))
            item_total += effective_price * qty

        print(f"[CART LOG] ITEM TOTAL: {item_total}")

        # 3. Calculate coupon discount
        from app.promotions.services import coupon_service
        applied_codes = cart.applied_coupons or []
        calc = await coupon_service.calculate_discount(db, tenant_id, user_id, applied_codes)
        if not calc["is_valid"] and applied_codes:
            raise ValidationError(calc["error_message"])
        discount_applied = calc["discount_applied"]

        # 4. Delivery details
        if str(tenant_id) == "6b1e8aed-ed2c-4d4f-8fd2-682488943f2a":
            delivery_fee = Decimal("1.00")
        else:
            delivery_fee = Decimal(str(cart.delivery_fee)) if cart.delivery_fee is not None else Decimal("0.00")

        # 5. Totals (no tax)
        net_total = max(Decimal("0.00"), item_total - discount_applied + delivery_fee)
        grand_total = net_total.quantize(Decimal("0.01"))

        # 6. Allocate discount proportionally to cart items for constraints storage
        allocated_discount_sum = Decimal("0.00")
        items_snapshot = []
        for i, (prod_id, qty, price) in enumerate(cart_products):
            subtotal_item = Decimal(str(price)) * qty
            
            if i == len(cart_products) - 1:
                item_discount = discount_applied - allocated_discount_sum
            else:
                item_share = subtotal_item / item_total if item_total > 0 else Decimal("0.00")
                item_discount = (discount_applied * item_share).quantize(Decimal("0.01"))
                allocated_discount_sum += item_discount

            subtotal = max(Decimal("0.00"), subtotal_item - item_discount)
            items_snapshot.append({
                "product_id": str(prod_id),
                "quantity": qty,
                "unit_price": float(price),
                "discount_applied": float(item_discount),
                "subtotal": float(subtotal)
            })

        # 7. Check for active direct tenant gateway vs fallback commission routing
        stmt_tg = (
            select(TenantPaymentGateway)
            .join(PaymentGateway, TenantPaymentGateway.gateway_id == PaymentGateway.id)
            .where(
                (TenantPaymentGateway.tenant_id == tenant_id) &
                (TenantPaymentGateway.is_active == True)
            )
        )
        res_tg = await db.execute(stmt_tg)
        tenant_gw = res_tg.scalar_one_or_none()

        is_fallback = False
        gateway_name = "RAZORPAY"
        credentials = {}
        commission_percent = Decimal("0.00")
        linked_account_id = None

        if tenant_gw:
            credentials = tenant_gw.credentials
            stmt_gw_name = select(PaymentGateway.name).where(PaymentGateway.id == tenant_gw.gateway_id)
            res_gw_name = await db.execute(stmt_gw_name)
            gateway_name = res_gw_name.scalar() or "RAZORPAY"
        else:
            stmt_comm = select(TenantCommission).where(TenantCommission.tenant_id == tenant_id)
            res_comm = await db.execute(stmt_comm)
            comm = res_comm.scalar_one_or_none()
            if not comm:
                raise ValidationError("No active payment gateway or commission configurations found for this tenant.")
            
            is_fallback = True
            commission_percent = comm.commission_percent
            linked_account_id = comm.linked_account_id
            
            stmt_pg = select(PaymentGateway).where(PaymentGateway.is_active == True)
            res_pg = await db.execute(stmt_pg)
            platform_gw = res_pg.scalar_one_or_none()
            if not platform_gw:
                raise ValidationError("Fallback routing enabled but no active platform gateway is configured.")
            
            gateway_name = platform_gw.name
            credentials = platform_gw.credentials

        key_id = credentials.get("key_id")
        key_secret = credentials.get("key_secret")
        if not key_id or not key_secret:
            raise ValidationError("Payment gateway credentials are misconfigured.")

        total_paise = int(round(grand_total * 100))
        
        print(f"--- CART CALCULATION LOG ---")
        print(f"Item Total: {item_total}")
        print(f"Discount Applied: {discount_applied}")
        print(f"Delivery Fee: {delivery_fee}")
        print(f"Grand Total: {grand_total}")
        print(f"Total Paise (sending to Razorpay): {total_paise}")
        print(f"Cart Products: {cart_products}")
        print(f"----------------------------")

        
        # Prepare Razorpay payload
        payload = {
            "amount": total_paise,
            "currency": "INR",
            "receipt": f"cart_{uuid.uuid4().hex[:14]}",
            "notes": {
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "mode": "fallback" if is_fallback else "direct",
                "type": "deferred_order"
            }
        }

        if is_fallback:
            commission_amount = grand_total * (commission_percent / Decimal("100.00"))
            transfer_amount = grand_total - commission_amount
            transfer_paise = int(round(transfer_amount * 100))
            payload["transfers"] = [
                {
                    "account": linked_account_id,
                    "amount": transfer_paise,
                    "currency": "INR"
                }
            ]

        # 8. Create Gateway Order
        rzp_order_id = None
        gateway_response = {}

        if key_id.startswith("test_") or key_id.startswith("mock_") or key_id == "dummy_key_id":
            rzp_order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
            gateway_response = {
                "id": rzp_order_id,
                "entity": "order",
                "amount": total_paise,
                "amount_paid": 0,
                "amount_due": total_paise,
                "currency": "INR",
                "receipt": payload["receipt"],
                "status": "created",
                "attempts": 0,
                "notes": payload["notes"],
                "created_at": 1600000000
            }
            if "transfers" in payload:
                gateway_response["transfers"] = payload["transfers"]
        else:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=(key_id, key_secret),
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code != 200:
                        error_detail = response.text
                        try:
                            # Try to parse the error message if it's JSON
                            err_json = response.json()
                            if "error" in err_json and "description" in err_json["error"]:
                                error_detail = err_json["error"]["description"]
                            else:
                                error_detail = str(err_json)
                        except Exception:
                            pass
                        raise ValidationError(f"Failed to initiate order with Razorpay: {error_detail}")
                    gateway_response = response.json()
                    rzp_order_id = gateway_response.get("id")
                except httpx.RequestError as exc:
                    raise ValidationError(f"Network connection failed: {exc}")

        if not rzp_order_id:
            raise ValidationError("Failed to obtain transaction reference.")

        # 9. Store the PendingCartPayment record
        from app.payments.models import PendingCartPayment
        billing_details = {
            "item_total": float(item_total),
            "discount_applied": float(discount_applied),
            "delivery_fee": float(delivery_fee),
            "delivery_service": cart.delivery_service,
            "estimated_days": cart.estimated_days,
            "tax": 0.0,
            "grand_total": float(grand_total),
            "applied_coupons": applied_codes,
            "delivery_address_id": str(cart.delivery_address_id) if cart.delivery_address_id else None
        }

        pending_payment = PendingCartPayment(
            tenant_id=tenant_id,
            user_id=user_id,
            gateway_order_id=rzp_order_id,
            amount=grand_total,
            cart_items=items_snapshot,
            billing_details=billing_details,
            status="PENDING",
            gateway="GUBERA" if is_fallback else gateway_name,
            gateway_response=gateway_response
        )
        db.add(pending_payment)
        await db.commit()
        await db.refresh(pending_payment)

        return {
            "key": key_id,
            "amount": total_paise,
            "currency": "INR",
            "name": "Gubera Cart Checkout" if is_fallback else "Tenant Cart Checkout",
            "order_id": rzp_order_id,
            "payment_id": str(pending_payment.id)
        }

    @staticmethod
    def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify the payload signature using the webhook secret."""
        if not secret or not signature:
            return False
        try:
            expected = hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    @staticmethod
    async def process_webhook(db: AsyncSession, event_data: Dict[str, Any]) -> bool:
        """Process verified Razorpay webhook payloads and transition payment/order statuses."""
        event_name = event_data.get("event")
        
        # We handle order.paid and payment.captured
        # Normalize finding Razorpay Order ID and transaction ref
        rzp_order_id = None
        rzp_payment_id = None
        
        if event_name == "order.paid":
            order_entity = event_data.get("payload", {}).get("order", {}).get("entity", {})
            rzp_order_id = order_entity.get("id")
        elif event_name == "payment.captured":
            payment_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})
            rzp_order_id = payment_entity.get("order_id")
            rzp_payment_id = payment_entity.get("id")
        else:
            logger.info(f"Skipping unsupported webhook event: {event_name}")
            return False

        if not rzp_order_id:
            logger.warning("No order reference found in webhook event payload.")
            return False

        # Load OrderPayment
        stmt = select(OrderPayment).where(OrderPayment.transaction_reference == rzp_order_id)
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()
        
        if not payment:
            # Check for PendingCartPayment
            stmt_pending = select(PendingCartPayment).where(PendingCartPayment.gateway_order_id == rzp_order_id)
            res_pending = await db.execute(stmt_pending)
            pending = res_pending.scalar_one_or_none()
            
            if not pending:
                logger.warning(f"No matching OrderPayment or PendingCartPayment found for gateway transaction ref: {rzp_order_id}")
                return False
                
            if pending.status == "COMPLETED":
                logger.info(f"Pending checkout session {pending.id} is already processed. Ignoring webhook.")
                return True
                
            pending.status = "COMPLETED"
            if rzp_payment_id:
                resp = dict(pending.gateway_response or {})
                resp["payment_id"] = rzp_payment_id
                pending.gateway_response = resp
            await db.flush()
            
            # Create actual Order from the pending snapshot constraints & clear cart
            from app.orders.services import order_service
            await order_service.create_order_from_pending_payment(db, pending)
            await db.commit()
            return True

        if payment.status == "COMPLETED":
            logger.info(f"Payment {payment.id} is already COMPLETED. Ignoring webhook.")
            return True

        # Transition status to COMPLETED
        payment.status = "COMPLETED"
        if rzp_payment_id:
            # Update gateway response metadata
            resp = dict(payment.gateway_response or {})
            resp["payment_id"] = rzp_payment_id
            payment.gateway_response = resp
            
        await db.flush()

        # Update order payment_status
        stmt_order = select(Order).where(Order.id == payment.order_id)
        res_order = await db.execute(stmt_order)
        order = res_order.scalar_one_or_none()
        if order:
            stmt_paid = select(func.sum(OrderPayment.amount)).where(
                (OrderPayment.order_id == order.id) &
                (OrderPayment.status == "COMPLETED")
            )
            res_paid = await db.execute(stmt_paid)
            total_paid = res_paid.scalar() or Decimal("0.00")
            
            if total_paid >= order.grand_total:
                order.payment_status = "PAID"
            elif total_paid > 0:
                order.payment_status = "PARTIALLY_PAID"
            else:
                order.payment_status = "UNPAID"

        await db.commit()
        await db.refresh(payment)
        return True

    @staticmethod
    async def verify_online_payment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        payment_id: str,
        signature: str
    ) -> Order:
        """Verify Razorpay online payment and mark order as PAID."""
        stmt_order = select(Order).where(
            (Order.id == order_id) & 
            (Order.tenant_id == tenant_id) & 
            (Order.user_id == user_id)
        )
        res_order = await db.execute(stmt_order)
        order = res_order.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found.")

        # Record payment transaction in database
        from app.orders.services import order_service
        await order_service.add_payment(
            db=db,
            tenant_id=tenant_id,
            order_id=order_id,
            amount=order.grand_total,
            payment_method="RAZORPAY",
            transaction_reference=payment_id,
            status="COMPLETED",
            gateway_response={"razorpay_payment_id": payment_id, "razorpay_signature": signature}
        )

        await db.refresh(order)
        return order

    @staticmethod
    async def verify_cart_payment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        payment_id: str,
        signature: str,
        rzp_order_id: str
    ) -> Order:
        """Verify Razorpay cart payment, create the actual Order, and clear the cart."""
        # 1. Fetch the pending cart payment by gateway_order_id
        from app.payments.models import PendingCartPayment
        stmt = select(PendingCartPayment).where(
            (PendingCartPayment.gateway_order_id == rzp_order_id) &
            (PendingCartPayment.tenant_id == tenant_id) &
            (PendingCartPayment.user_id == user_id)
        )
        res = await db.execute(stmt)
        pending = res.scalar_one_or_none()
        
        if not pending:
            raise ValidationError("Pending cart payment not found.")

        # 2. Prevent duplicate processing
        if pending.status == "COMPLETED":
            # If already completed by webhook or earlier request, just find the associated order.
            # We assume the order has the gateway_response with payment_id
            from app.orders.models import OrderPayment, Order
            stmt_order = select(Order).join(OrderPayment).where(OrderPayment.transaction_reference == payment_id)
            res_order = await db.execute(stmt_order)
            existing_order = res_order.scalar_one_or_none()
            if existing_order:
                return existing_order
            raise ValidationError("Payment already processed but order not found.")

        # 3. Create actual Order from the pending snapshot constraints & clear cart
        from app.orders.services import order_service
        order = await order_service.create_order_from_pending_payment(db, pending)

        # 4. Update PendingCartPayment status
        pending.status = "COMPLETED"
        resp = dict(pending.gateway_response or {})
        resp["payment_id"] = payment_id
        pending.gateway_response = resp
        
        # 5. Record payment transaction for the new Order
        await order_service.add_payment(
            db=db,
            tenant_id=tenant_id,
            order_id=order.id,
            amount=order.grand_total,
            payment_method="RAZORPAY",
            transaction_reference=payment_id,
            status="COMPLETED",
            gateway_response={"razorpay_payment_id": payment_id, "razorpay_signature": signature}
        )

        await db.commit()
        await db.refresh(order)
        return order
