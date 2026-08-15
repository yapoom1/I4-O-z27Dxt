import uuid
import math
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import UserCart, UserAddress
from app.utils.exceptions import ValidationError

TENANT_ORIGIN_LAT = 12.9716
TENANT_ORIGIN_LON = 77.5946
TENANT_ORIGIN_PINCODE = "560001"

class DeliveryService:
    """Service layer handling dynamic mock delivery quotes and options configuration."""

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great-circle distance between two points in kilometers."""
        R = 6371.0  # Earth radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def parse_lat_long(lat_long_str: Optional[str]) -> Optional[tuple[float, float]]:
        """Parse 'lat,lon' string into float coordinates."""
        if not lat_long_str:
            return None
        try:
            parts = lat_long_str.split(",")
            if len(parts) == 2:
                return float(parts[0].strip()), float(parts[1].strip())
        except Exception:
            pass
        return None

    @staticmethod
    async def get_delivery_quotes(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        address_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Generate Standard and Express quotes (temporarily 0.00 until Shiprocket is used)."""
        # 1. Fetch UserAddress
        stmt = select(UserAddress).where(UserAddress.id == address_id)
        res = await db.execute(stmt)
        address = res.scalar_one_or_none()
        if not address:
            raise ValidationError("Address not found.")

        # Try Shiprocket if configured
        from app.tenants.services import tenant_service
        tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
        
        if tenant and getattr(tenant, 'shiprocket_email', None) and getattr(tenant, 'shiprocket_password', None):
            from app.deliveries.shiprocket_service import shiprocket_service
            import re
            user_pin = address.pincode.strip() if address.pincode else ""
            
            # Smart fallback: if pincode is 000000 or invalid 5-digit/6-digit, try extracting a 6-digit PIN from district/address fields
            if not user_pin or len(user_pin) != 6 or user_pin == "000000":
                search_text = f"{address.pincode or ''} {address.district or ''} {address.address_line_1 or ''} {address.state or ''}"
                match = re.search(r'\b[1-9][0-9]{5}\b', search_text)
                if match:
                    user_pin = match.group(0)

            if user_pin and len(user_pin) == 6:
                total_weight = 1.0
                if address.user_id:
                    from app.users.services import user_service
                    cart = await user_service.get_or_create_cart(db, tenant_id, address.user_id)
                    if cart and cart.items:
                        from app.products.products.services import product_service
                        weight_sum = 0.0
                        for item in cart.items:
                            prod = await product_service.get_product_by_id(tenant_id, item.product_id)
                            item_weight = 0.5
                            if prod and getattr(prod, 'shipping', None) and prod.shipping.weight:
                                item_weight = prod.shipping.weight
                            weight_sum += item_weight * item.quantity
                        if weight_sum > 0:
                            total_weight = weight_sum

                sr_quotes = await shiprocket_service.get_rates(
                    db=db,
                    tenant=tenant,
                    pickup_pincode=TENANT_ORIGIN_PINCODE,
                    delivery_pincode=user_pin,
                    weight=total_weight
                )
                if sr_quotes:
                    return sr_quotes

        # Temporarily 0.00 delivery fee (Free delivery until Shiprocket is configured)
        return [
            {
                "service_name": "Standard",
                "delivery_fee": Decimal("0.00"),
                "estimated_days": 3
            },
            {
                "service_name": "Express",
                "delivery_fee": Decimal("0.00"),
                "estimated_days": 1
            }
        ]

    @staticmethod
    async def apply_delivery_to_cart(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        address_id: uuid.UUID,
        service_name: str
    ) -> UserCart:
        """Calculate quotes for specified address, find selection, and write details onto the user's cart."""
        # 1. Fetch address to make sure it belongs to user
        stmt_addr = select(UserAddress).where((UserAddress.id == address_id) & (UserAddress.user_id == user_id))
        res_addr = await db.execute(stmt_addr)
        address = res_addr.scalar_one_or_none()
        if not address:
            raise ValidationError("Delivery address not found or does not belong to the user.")

        # 2. Get Quotes
        quotes = await DeliveryService.get_delivery_quotes(db, tenant_id, address_id)
        selected_quote = None
        for q in quotes:
            if q["service_name"].upper() == service_name.strip().upper():
                selected_quote = q
                break

        if not selected_quote:
            raise ValidationError(f"Delivery service option '{service_name}' not available.")

        # 3. Fetch User's Cart
        stmt_cart = select(UserCart).where(UserCart.user_id == user_id)
        res_cart = await db.execute(stmt_cart)
        cart = res_cart.scalar_one_or_none()
        if not cart:
            from app.users.services import user_service
            cart = await user_service.get_or_create_cart(db, tenant_id, user_id)

        # 4. Save fields onto Cart
        cart.delivery_fee = selected_quote["delivery_fee"]
        cart.delivery_service = selected_quote["service_name"]
        cart.estimated_days = selected_quote["estimated_days"]
        cart.delivery_address_id = address_id

        await db.commit()
        await db.refresh(cart)
        return cart

delivery_service = DeliveryService()

class DeliveryRuleService:
    @staticmethod
    async def get_delivery_rules(db: AsyncSession, tenant_id: uuid.UUID):
        from app.deliveries.models import DeliveryRule
        stmt = select(DeliveryRule).where(DeliveryRule.tenant_id == tenant_id)
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def create_delivery_rule(db: AsyncSession, tenant_id: uuid.UUID, field: str, operator: str, value: str, carrier: str):
        from app.deliveries.models import DeliveryRule
        rule = DeliveryRule(
            tenant_id=tenant_id,
            field=field,
            operator=operator,
            value=value,
            carrier=carrier
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def update_delivery_rule(db: AsyncSession, tenant_id: uuid.UUID, rule_id: uuid.UUID, **kwargs):
        from app.deliveries.models import DeliveryRule
        stmt = select(DeliveryRule).where(DeliveryRule.id == rule_id, DeliveryRule.tenant_id == tenant_id)
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            raise ValidationError("Delivery rule not found or access denied.")

        for k, v in kwargs.items():
            setattr(rule, k, v)

        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete_delivery_rule(db: AsyncSession, tenant_id: uuid.UUID, rule_id: uuid.UUID):
        from app.deliveries.models import DeliveryRule
        stmt = select(DeliveryRule).where(DeliveryRule.id == rule_id, DeliveryRule.tenant_id == tenant_id)
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            raise ValidationError("Delivery rule not found or access denied.")
        
        await db.delete(rule)
        await db.commit()
        return True

delivery_rule_service = DeliveryRuleService()

class DeliveryAgentService:
    @staticmethod
    async def get_delivery_agents(db: AsyncSession, tenant_id: uuid.UUID):
        from app.deliveries.models import DeliveryAgent
        stmt = select(DeliveryAgent).where(DeliveryAgent.tenant_id == tenant_id).order_by(DeliveryAgent.created_at.desc())
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def create_delivery_agent(db: AsyncSession, tenant_id: uuid.UUID, name: str, zone: str):
        from app.deliveries.models import DeliveryAgent
        agent = DeliveryAgent(
            tenant_id=tenant_id,
            name=name,
            zone=zone
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent

delivery_agent_service = DeliveryAgentService()
