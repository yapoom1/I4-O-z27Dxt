import uuid
from datetime import datetime
from typing import Optional, List, Annotated
import strawberry
from decimal import Decimal

from app.orders.services import order_service
from app.products.products.graphql import ProductType
from app.users.graphql import UserAddressType
from app.utils.exceptions import UnauthorizedError, ValidationError
from app.orders.models import Order as DBOrder, OrderItem as DBOrderItem, OrderPayment as DBOrderPayment, OrderReturn as DBOrderReturn, OrderReturnItem as DBOrderReturnItem

@strawberry.type
class OrderItemType:
    id: uuid.UUID
    order_id: uuid.UUID = strawberry.field(name="orderId")
    product_id: uuid.UUID = strawberry.field(name="productId")
    quantity: int
    unit_price: float = strawberry.field(name="unitPrice")
    discount_applied: float = strawberry.field(name="discountApplied")
    subtotal: float

    @strawberry.field
    async def product(self, info: strawberry.Info) -> ProductType:
        from app.products.products.services import product_service
        db = info.context.db
        tenant_id = info.context.tenant_id or (info.context.user.tenant_id if info.context.user else None)
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        db_product = await product_service.get_product_by_id(tenant_id, self.product_id)
        if not db_product:
            raise ValidationError("Product not found.")
        return ProductType(db_product)

    def __init__(self, db_item: DBOrderItem):
        self.id = db_item.id
        self.order_id = db_item.order_id
        self.product_id = db_item.product_id
        self.quantity = db_item.quantity
        self.unit_price = float(db_item.unit_price)
        self.discount_applied = float(db_item.discount_applied)
        self.subtotal = float(db_item.subtotal)


@strawberry.type
class OrderPaymentType:
    id: uuid.UUID
    order_id: uuid.UUID = strawberry.field(name="orderId")
    amount: float
    payment_method: str = strawberry.field(name="paymentMethod")
    status: str
    transaction_reference: Optional[str] = strawberry.field(name="transactionReference")
    gateway_response: strawberry.scalars.JSON = strawberry.field(name="gatewayResponse")
    created_at: datetime = strawberry.field(name="createdAt")

    def __init__(self, db_pay: DBOrderPayment):
        self.id = db_pay.id
        self.order_id = db_pay.order_id
        self.amount = float(db_pay.amount)
        self.payment_method = db_pay.payment_method
        self.status = db_pay.status
        self.transaction_reference = db_pay.transaction_reference
        self.gateway_response = db_pay.gateway_response
        self.created_at = db_pay.created_at


@strawberry.type
class OrderReturnItemType:
    id: uuid.UUID
    order_return_id: uuid.UUID = strawberry.field(name="orderReturnId")
    order_item_id: uuid.UUID = strawberry.field(name="orderItemId")
    quantity: int
    condition: str

    def __init__(self, db_ret_item: DBOrderReturnItem):
        self.id = db_ret_item.id
        self.order_return_id = db_ret_item.order_return_id
        self.order_item_id = db_ret_item.order_item_id
        self.quantity = db_ret_item.quantity
        self.condition = db_ret_item.condition


@strawberry.type
class OrderReturnType:
    id: uuid.UUID
    order_id: uuid.UUID = strawberry.field(name="orderId")
    reason: str
    status: str
    refund_status: str = strawberry.field(name="refundStatus")
    refund_amount: float = strawberry.field(name="refundAmount")
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def items(self, info: strawberry.Info) -> List[OrderReturnItemType]:
        db = info.context.db
        from sqlalchemy import select
        stmt = select(DBOrderReturnItem).where(DBOrderReturnItem.order_return_id == self.id)
        res = await db.execute(stmt)
        db_items = res.scalars().all()
        return [OrderReturnItemType(item) for item in db_items]

    def __init__(self, db_ret: DBOrderReturn):
        self.id = db_ret.id
        self.order_id = db_ret.order_id
        self.reason = db_ret.reason
        self.status = db_ret.status
        self.refund_status = db_ret.refund_status
        self.refund_amount = float(db_ret.refund_amount)
        self.created_at = db_ret.created_at


@strawberry.type
class OrderType:
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    delivery_address_id: Optional[uuid.UUID] = strawberry.field(name="deliveryAddressId")
    delivery_service: Optional[str] = strawberry.field(name="deliveryService")
    delivery_fee: float = strawberry.field(name="deliveryFee")
    estimated_days: Optional[int] = strawberry.field(name="estimatedDays")
    item_total: float = strawberry.field(name="itemTotal")
    discount_applied: float = strawberry.field(name="discountApplied")
    tax: float
    grand_total: float = strawberry.field(name="grandTotal")
    order_status: str = strawberry.field(name="orderStatus")
    payment_status: str = strawberry.field(name="paymentStatus")
    applied_coupons: List[str] = strawberry.field(name="appliedCoupons")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def items(self, info: strawberry.Info) -> List[OrderItemType]:
        db = info.context.db
        from sqlalchemy import select
        stmt = select(DBOrderItem).where(DBOrderItem.order_id == self.id)
        res = await db.execute(stmt)
        db_items = res.scalars().all()
        return [OrderItemType(item) for item in db_items]

    @strawberry.field
    async def payments(self, info: strawberry.Info) -> List[OrderPaymentType]:
        db = info.context.db
        from sqlalchemy import select
        stmt = select(DBOrderPayment).where(DBOrderPayment.order_id == self.id)
        res = await db.execute(stmt)
        db_payments = res.scalars().all()
        return [OrderPaymentType(p) for p in db_payments]

    @strawberry.field
    async def returns(self, info: strawberry.Info) -> List[OrderReturnType]:
        db = info.context.db
        from sqlalchemy import select
        stmt = select(DBOrderReturn).where(DBOrderReturn.order_id == self.id)
        res = await db.execute(stmt)
        db_returns = res.scalars().all()
        return [OrderReturnType(r) for r in db_returns]

    @strawberry.field
    async def delivery_address(self, info: strawberry.Info) -> Optional[UserAddressType]:
        if not self.delivery_address_id:
            return None
        db = info.context.db
        from app.users.models import UserAddress
        from sqlalchemy import select
        stmt = select(UserAddress).where(UserAddress.id == self.delivery_address_id)
        res = await db.execute(stmt)
        addr = res.scalar_one_or_none()
        return UserAddressType(addr) if addr else None

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        if not self.user_id:
            return None
        db = info.context.db
        from app.users.models import User
        from sqlalchemy import select
        stmt = select(User).where(User.id == self.user_id)
        res = await db.execute(stmt)
        u = res.scalar_one_or_none()
        if not u:
            return None
        from app.users.graphql import UserType
        return UserType(u)

    def __init__(self, db_order: DBOrder):
        self.id = db_order.id
        self.user_id = db_order.user_id
        self.delivery_address_id = db_order.delivery_address_id
        self.delivery_service = db_order.delivery_service
        self.delivery_fee = float(db_order.delivery_fee)
        self.estimated_days = db_order.estimated_days
        self.item_total = float(db_order.item_total)
        self.discount_applied = float(db_order.discount_applied)
        self.tax = float(db_order.tax)
        self.grand_total = float(db_order.grand_total)
        self.order_status = db_order.order_status
        self.payment_status = db_order.payment_status
        self.applied_coupons = db_order.applied_coupons or []
        self.created_at = db_order.created_at
        self.updated_at = db_order.updated_at


@strawberry.input
class ReturnItemInput:
    order_item_id: uuid.UUID = strawberry.field(name="orderItemId")
    quantity: int
    condition: str  # UNOPENED, DAMAGED, DEFECTIVE


@strawberry.input
class RequestReturnInput:
    order_id: uuid.UUID = strawberry.field(name="orderId")
    reason: str
    items: List[ReturnItemInput]


@strawberry.type
class OrderQuery:
    @strawberry.field
    async def my_orders(self, info: strawberry.Info) -> List[OrderType]:
        """Fetch all orders placed by the currently authenticated customer."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from sqlalchemy import select
        stmt = select(DBOrder).where((DBOrder.tenant_id == tenant_id) & (DBOrder.user_id == current_user.id)).order_by(DBOrder.created_at.desc())
        res = await db.execute(stmt)
        orders = res.scalars().all()
        return [OrderType(o) for o in orders]

    @strawberry.field
    async def order(self, info: strawberry.Info, id: uuid.UUID) -> Optional[OrderType]:
        """Fetch details of a single order by ID."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from sqlalchemy import select
        stmt = select(DBOrder).where((DBOrder.id == id) & (DBOrder.tenant_id == tenant_id))
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            return None

        # Verify access: customer can only see their own order, admins can see any order
        if current_user.role == "USER" and order.user_id != current_user.id:
            raise UnauthorizedError("Access denied.")

        return OrderType(order)

    @strawberry.field
    async def tenant_orders(self, info: strawberry.Info, status: Optional[str] = None) -> List[OrderType]:
        """Fetch all orders under the current tenant (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only administrators can view all tenant orders.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        from sqlalchemy import select
        stmt = select(DBOrder).where(DBOrder.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(DBOrder.order_status == status)
        stmt = stmt.order_by(DBOrder.created_at.desc())

        res = await db.execute(stmt)
        orders = res.scalars().all()
        return [OrderType(o) for o in orders]


@strawberry.type
class OrderMutation:
    @strawberry.mutation
    async def checkout_cart(
        self,
        info: strawberry.Info,
        payment_method: str = "CARD"
    ) -> OrderType:
        """Process checkout: convert shopping cart to Order, log coupon redemptions, and clear the cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        order = await order_service.checkout_cart(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            payment_method=payment_method
        )
        return OrderType(order)

    @strawberry.mutation
    async def record_payment(
        self,
        info: strawberry.Info,
        order_id: uuid.UUID,
        amount: float,
        payment_method: str,
        transaction_reference: Optional[str] = None,
        status: str = "COMPLETED"
    ) -> OrderPaymentType:
        """Record a payment transaction for an order."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        # Customers can record payments for their own orders; admins can record for any
        from sqlalchemy import select
        stmt = select(DBOrder).where(DBOrder.id == order_id)
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            raise ValidationError("Order not found.")
        if current_user.role == "USER" and order.user_id != current_user.id:
            raise UnauthorizedError("Access denied.")

        payment = await order_service.add_payment(
            db=db,
            tenant_id=tenant_id,
            order_id=order_id,
            amount=Decimal(str(amount)),
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            status=status
        )
        return OrderPaymentType(payment)

    @strawberry.mutation
    async def request_order_return(
        self,
        info: strawberry.Info,
        input: RequestReturnInput
    ) -> OrderReturnType:
        """Submit an order return request for review."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        returned_items_dicts = [
            {
                "order_item_id": item.order_item_id,
                "quantity": item.quantity,
                "condition": item.condition
            }
            for item in input.items
        ]

        order_return = await order_service.request_return(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            order_id=input.order_id,
            reason=input.reason,
            return_items=returned_items_dicts
        )
        return OrderReturnType(order_return)

    @strawberry.mutation
    async def approve_order_return(
        self,
        info: strawberry.Info,
        return_id: uuid.UUID,
        approved: bool
    ) -> OrderReturnType:
        """Approve or reject a return request (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only administrators can approve returns.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        order_return = await order_service.approve_return(
            db=db,
            tenant_id=tenant_id,
            return_id=return_id,
            approved=approved
        )
        return OrderReturnType(order_return)

    @strawberry.mutation
    async def complete_order_return(
        self,
        info: strawberry.Info,
        return_id: uuid.UUID,
        refund_amount: float
    ) -> OrderReturnType:
        """Mark return request as resolved and issue a refund balance (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only administrators can complete returns.")

        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        order_return = await order_service.complete_return(
            db=db,
            tenant_id=tenant_id,
            return_id=return_id,
            refund_amount=Decimal(str(refund_amount))
        )
        return OrderReturnType(order_return)

    @strawberry.mutation
    async def update_order_delivery_status(
        self,
        info: strawberry.Info,
        order_id: uuid.UUID,
        status: str
    ) -> OrderType:
        """Manually update the delivery/order status (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only administrators can update order status.")
            
        db = info.context.db
        
        # Determine the tenant constraints based on role
        filter_tenant_id = None
        if current_user.role == "TENANT_ADMIN":
            filter_tenant_id = info.context.tenant_id or current_user.tenant_id
            if not filter_tenant_id:
                raise ValidationError("Tenant ID context is missing.")

        order = await order_service.update_order_status(
            db=db,
            order_id=order_id,
            status=status,
            tenant_id=filter_tenant_id
        )
        return OrderType(order)

    @strawberry.mutation
    async def update_order_payment_status(
        self,
        info: strawberry.Info,
        order_id: uuid.UUID,
        status: str
    ) -> OrderType:
        """Manually update the payment status (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("Only administrators can update payment status.")
            
        db = info.context.db
        
        filter_tenant_id = None
        if current_user.role == "TENANT_ADMIN":
            filter_tenant_id = info.context.tenant_id or current_user.tenant_id
            if not filter_tenant_id:
                raise ValidationError("Tenant ID context is missing.")

        order = await order_service.update_order_payment_status(
            db=db,
            order_id=order_id,
            status=status,
            tenant_id=filter_tenant_id
        )
        return OrderType(order)
