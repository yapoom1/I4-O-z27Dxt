import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order, OrderItem, OrderPayment, OrderReturn, OrderReturnItem
from app.users.models import UserCart, CartItem
from app.products.products.models import Product
from app.products.pricing.models import ProductPrice, PricingType
from app.promotions.models import Coupon, CouponUsage
from app.promotions.services import coupon_service
from app.utils.exceptions import ValidationError

class OrderService:
    """Service layer handling creation, retrieval, status lifecycle, payments, and returns of orders."""

    @staticmethod
    async def checkout_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        payment_method: str
    ) -> Order:
        """Create a new Order from the user's active shopping cart, log coupon usages, and clear the cart."""
        # 1. Fetch user's cart
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
        for prod_id, qty, stock in items:
            effective_price = await PricingService.get_effective_price(
                db=db,
                tenant_id=tenant_id,
                product_id=prod_id,
                quantity=qty,
                location_id=None,
                pincode=pincode,
                current_time=None,
                current_stock=stock
            )
            cart_products.append((prod_id, qty, effective_price))
            item_total += effective_price * qty

        # 3. Calculate coupon discount
        applied_codes = cart.applied_coupons or []
        calc = await coupon_service.calculate_discount(db, tenant_id, user_id, applied_codes)
        if not calc["is_valid"] and applied_codes:
            raise ValidationError(calc["error_message"])
        discount_applied = calc["discount_applied"]

        # 4. Delivery details
        delivery_fee = Decimal(str(cart.delivery_fee)) if cart.delivery_fee is not None else Decimal("0.00")

        # 5. Totals & Tax (5%)
        net_total = max(Decimal("0.00"), item_total - discount_applied + delivery_fee)
        tax = (net_total * Decimal("0.05")).quantize(Decimal("0.01"))
        grand_total = (net_total + tax).quantize(Decimal("0.01"))

        # 6. Create Order
        order = Order(
            tenant_id=tenant_id,
            user_id=user_id,
            delivery_address_id=cart.delivery_address_id,
            delivery_service=cart.delivery_service,
            delivery_fee=delivery_fee,
            estimated_days=cart.estimated_days,
            item_total=item_total,
            discount_applied=discount_applied,
            tax=tax,
            grand_total=grand_total,
            order_status="PENDING",
            payment_status="UNPAID",
            applied_coupons=applied_codes
        )
        db.add(order)
        await db.flush()  # Generate order.id

        # 7. Create OrderItems and allocate discount proportionally
        allocated_discount_sum = Decimal("0.00")
        for i, (prod_id, qty, price) in enumerate(cart_products):
            subtotal_item = Decimal(str(price)) * qty
            
            if i == len(cart_products) - 1:
                item_discount = discount_applied - allocated_discount_sum
            else:
                item_share = subtotal_item / item_total if item_total > 0 else Decimal("0.00")
                item_discount = (discount_applied * item_share).quantize(Decimal("0.01"))
                allocated_discount_sum += item_discount

            subtotal = max(Decimal("0.00"), subtotal_item - item_discount)
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=prod_id,
                quantity=qty,
                unit_price=Decimal(str(price)),
                discount_applied=item_discount,
                subtotal=subtotal
            )
            db.add(order_item)

        # 8. Record Coupon usage ledgers & increment coupon usage count
        for code in applied_codes:
            coupon = await coupon_service.get_coupon_by_code(db, tenant_id, code)
            if coupon:
                coupon.usage_count += 1
                usage = CouponUsage(
                    tenant_id=tenant_id,
                    coupon_id=coupon.id,
                    user_id=user_id,
                    order_id=order.id,
                    discount_applied=discount_applied  # Log absolute discount or share
                )
                db.add(usage)

        # 9. Clear the cart items & reset cart attributes
        for item in cart_items:
            await db.delete(item)
        
        cart.applied_coupons = []
        cart.delivery_fee = None
        cart.delivery_service = None
        cart.estimated_days = None
        cart.delivery_address_id = None
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cart, "applied_coupons")

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def add_payment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        order_id: uuid.UUID,
        amount: Decimal,
        payment_method: str,
        transaction_reference: Optional[str] = None,
        status: str = "COMPLETED",
        gateway_response: Optional[Dict[str, Any]] = None
    ) -> OrderPayment:
        """Record a payment attempt/success, updating the order's overall payment status dynamically."""
        # 1. Fetch Order
        stmt = select(Order).where((Order.id == order_id) & (Order.tenant_id == tenant_id))
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found.")

        # 2. Add Payment record
        payment = OrderPayment(
            order_id=order_id,
            tenant_id=tenant_id,
            amount=amount,
            payment_method=payment_method,
            status=status,
            transaction_reference=transaction_reference,
            gateway_response=gateway_response or {}
        )
        db.add(payment)
        await db.flush()

        # 3. Recalculate paid totals
        stmt_paid = select(func.sum(OrderPayment.amount)).where(
            (OrderPayment.order_id == order_id) &
            (OrderPayment.status == "COMPLETED")
        )
        res_paid = await db.execute(stmt_paid)
        total_paid = res_paid.scalar() or Decimal("0.00")

        # Update order status
        if total_paid >= order.grand_total:
            order.payment_status = "PAID"
        elif total_paid > 0:
            order.payment_status = "PARTIALLY_PAID"
        else:
            order.payment_status = "UNPAID"

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def request_return(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        reason: str,
        return_items: List[Dict[str, Any]]
    ) -> OrderReturn:
        """Create a return request for specified quantities of order items after validating return limits."""
        # 1. Validate Order exists and belongs to user
        stmt_order = select(Order).where((Order.id == order_id) & (Order.tenant_id == tenant_id) & (Order.user_id == user_id))
        res_order = await db.execute(stmt_order)
        order = res_order.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found or access denied.")

        # 2. Create OrderReturn request
        order_return = OrderReturn(
            order_id=order_id,
            tenant_id=tenant_id,
            reason=reason,
            status="PENDING_APPROVAL",
            refund_status="PENDING",
            refund_amount=Decimal("0.00")
        )
        db.add(order_return)
        await db.flush()

        # 3. Process and validate returned items
        for ri in return_items:
            order_item_id = ri["order_item_id"]
            quantity = ri["quantity"]
            condition = ri["condition"]

            # Validate original order item
            stmt_item = select(OrderItem).where((OrderItem.id == order_item_id) & (OrderItem.order_id == order_id))
            res_item = await db.execute(stmt_item)
            order_item = res_item.scalar_one_or_none()
            if not order_item:
                raise ValidationError(f"Order item '{order_item_id}' not found in this order.")

            # Validate remaining returnable limit
            stmt_returned = select(func.sum(OrderReturnItem.quantity)).join(
                OrderReturn, OrderReturn.id == OrderReturnItem.order_return_id
            ).where(
                (OrderReturnItem.order_item_id == order_item_id) &
                (OrderReturn.status.in_(["PENDING_APPROVAL", "APPROVED", "COMPLETED"]))
            )
            res_returned = await db.execute(stmt_returned)
            already_returned = res_returned.scalar() or 0
            returnable_qty = order_item.quantity - already_returned

            if quantity > returnable_qty:
                raise ValidationError(
                    f"Cannot return {quantity} units of item '{order_item_id}'. Only {returnable_qty} returnable units remain."
                )

            # Add return item
            ret_item = OrderReturnItem(
                order_return_id=order_return.id,
                order_item_id=order_item_id,
                quantity=quantity,
                condition=condition
            )
            db.add(ret_item)

        await db.commit()
        await db.refresh(order_return)
        return order_return

    @staticmethod
    async def approve_return(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        return_id: uuid.UUID,
        approved: bool
    ) -> OrderReturn:
        """Approve or reject a customer return request."""
        stmt = select(OrderReturn).where((OrderReturn.id == return_id) & (OrderReturn.tenant_id == tenant_id))
        res = await db.execute(stmt)
        order_return = res.scalar_one_or_none()
        if not order_return:
            raise ValidationError("Return request not found.")

        if approved:
            order_return.status = "APPROVED"
        else:
            order_return.status = "REJECTED"
            order_return.refund_status = "NO_REFUND"

        await db.commit()
        await db.refresh(order_return)
        return order_return

    @staticmethod
    async def update_order_status(
        db: AsyncSession,
        order_id: uuid.UUID,
        status: str,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Order:
        """Update the delivery/order status manually."""
        stmt = select(Order).where(Order.id == order_id)
        if tenant_id:
            stmt = stmt.where(Order.tenant_id == tenant_id)
            
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found or access denied.")
            
        order.order_status = status
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def update_order_payment_status(
        db: AsyncSession,
        order_id: uuid.UUID,
        status: str,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Order:
        """Update the payment status manually."""
        stmt = select(Order).where(Order.id == order_id)
        if tenant_id:
            stmt = stmt.where(Order.tenant_id == tenant_id)
            
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found or access denied.")
            
        order.payment_status = status
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def complete_return(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        return_id: uuid.UUID,
        refund_amount: Decimal
    ) -> OrderReturn:
        """Mark return request as completed, balance refund payments ledger, and transition order states."""
        # 1. Fetch Return Request
        stmt = select(OrderReturn).where((OrderReturn.id == return_id) & (OrderReturn.tenant_id == tenant_id))
        res = await db.execute(stmt)
        order_return = res.scalar_one_or_none()
        if not order_return:
            raise ValidationError("Return request not found.")

        # 2. Update status details
        order_return.status = "COMPLETED"
        order_return.refund_status = "REFUNDED"
        order_return.refund_amount = refund_amount
        await db.flush()

        # 3. Create negative OrderPayment entry for refund ledger balancing
        refund_payment = OrderPayment(
            order_id=order_return.order_id,
            tenant_id=tenant_id,
            amount=-refund_amount,
            payment_method="REFUND",
            status="REFUNDED",
            gateway_response={"notes": "Return request completed refund"}
        )
        db.add(refund_payment)

        # 4. Fetch Order to dynamically evaluate partial/full return status
        stmt_order = select(Order).where(Order.id == order_return.order_id)
        res_order = await db.execute(stmt_order)
        order = res_order.scalar_one()

        # Recalculate original order item count vs returned completed items
        stmt_original_qty = select(func.sum(OrderItem.quantity)).where(OrderItem.order_id == order.id)
        res_orig = await db.execute(stmt_original_qty)
        total_orig_qty = res_orig.scalar() or 0

        stmt_returned_qty = select(func.sum(OrderReturnItem.quantity)).join(
            OrderReturn, OrderReturn.id == OrderReturnItem.order_return_id
        ).where(
            (OrderReturn.order_id == order.id) &
            (OrderReturn.status == "COMPLETED")
        )
        res_ret = await db.execute(stmt_returned_qty)
        total_ret_qty = res_ret.scalar() or 0

        if total_ret_qty >= total_orig_qty:
            order.order_status = "RETURNED"
            order.payment_status = "REFUNDED"
        elif total_ret_qty > 0:
            order.order_status = "PARTIALLY_RETURNED"
            order.payment_status = "REFUNDED"  # Could also be partially refunded depending on accounting

        await db.commit()
        await db.refresh(order_return)
        return order_return

    @staticmethod
    async def create_order_from_pending_payment(
        db: AsyncSession,
        pending: Any
    ) -> Order:
        """Create a new Order directly from a completed PendingCartPayment session.
        Uses exact stored pricing constraints, logs coupon usages, and clears the cart."""
        
        # 1. Fetch user's cart to clear it at the end
        stmt_cart = select(UserCart).where(UserCart.user_id == pending.user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        
        if cart:
            # Load cart items to clear them
            stmt_cart_items = select(CartItem).where(CartItem.cart_id == cart.id)
            res_cart_items = await db.execute(stmt_cart_items)
            cart_items = res_cart_items.scalars().all()
        else:
            cart_items = []
            
        bd = pending.billing_details
        
        # 2. Reconstruct/Retrieve fields
        delivery_address_id = uuid.UUID(bd["delivery_address_id"]) if bd.get("delivery_address_id") else None
        
        # 3. Create the Order in PENDING status but PAID payment_status
        order = Order(
            tenant_id=pending.tenant_id,
            user_id=pending.user_id,
            delivery_address_id=delivery_address_id,
            delivery_service=bd.get("delivery_service"),
            delivery_fee=Decimal(str(bd.get("delivery_fee", 0.00))),
            estimated_days=bd.get("estimated_days"),
            item_total=Decimal(str(bd.get("item_total", 0.00))),
            discount_applied=Decimal(str(bd.get("discount_applied", 0.00))),
            tax=Decimal(str(bd.get("tax", 0.00))),
            grand_total=Decimal(str(bd.get("grand_total", 0.00))),
            order_status="PENDING",
            payment_status="PAID",
            applied_coupons=bd.get("applied_coupons", [])
        )
        db.add(order)
        await db.flush()  # Generate order.id
        
        # 4. Create OrderItem records from snapshot
        for item in pending.cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=uuid.UUID(item["product_id"]),
                quantity=item["quantity"],
                unit_price=Decimal(str(item["unit_price"])),
                discount_applied=Decimal(str(item["discount_applied"])),
                subtotal=Decimal(str(item["subtotal"]))
            )
            db.add(order_item)
            
        # 5. Record Coupon usages
        for code in bd.get("applied_coupons", []):
            coupon = await coupon_service.get_coupon_by_code(db, pending.tenant_id, code)
            if coupon:
                coupon.usage_count += 1
                usage = CouponUsage(
                    tenant_id=pending.tenant_id,
                    coupon_id=coupon.id,
                    user_id=pending.user_id,
                    order_id=order.id,
                    discount_applied=Decimal(str(bd.get("discount_applied", 0.00)))
                )
                db.add(usage)
                
        # 6. Clear user's cart items
        for item in cart_items:
            await db.delete(item)
            
        if cart:
            cart.applied_coupons = []
            cart.delivery_fee = None
            cart.delivery_service = None
            cart.estimated_days = None
            cart.delivery_address_id = None
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(cart, "applied_coupons")
            
        # 7. Create completed OrderPayment transaction record
        payment = OrderPayment(
            order_id=order.id,
            tenant_id=pending.tenant_id,
            amount=pending.amount,
            payment_method="ONLINE",
            status="COMPLETED",
            transaction_reference=pending.gateway_order_id,
            gateway=pending.gateway,
            gateway_response=pending.gateway_response
        )
        db.add(payment)
        
        await db.flush()
        return order


from typing import Any
order_service = OrderService()
