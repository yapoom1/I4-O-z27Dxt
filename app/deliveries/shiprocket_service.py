import httpx
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.tenants.models import Tenant
from app.utils.security import decrypt_password

logger = logging.getLogger(__name__)

class ShiprocketService:
    BASE_URL = "https://apiv2.shiprocket.in/v1/external"

    @staticmethod
    async def get_valid_token(db: AsyncSession, tenant: Tenant) -> Optional[str]:
        if not tenant.shiprocket_email or not tenant.shiprocket_password:
            return None

        now = datetime.utcnow()
        if tenant.shiprocket_token and tenant.shiprocket_token_expires and tenant.shiprocket_token_expires > now:
            return tenant.shiprocket_token

        # Need to re-authenticate
        password = decrypt_password(tenant.shiprocket_password)
        if not password:
            logger.error("Failed to decrypt Shiprocket password.")
            return None

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{ShiprocketService.BASE_URL}/auth/login",
                    json={
                        "email": tenant.shiprocket_email,
                        "password": password
                    }
                )
                res.raise_for_status()
                data = res.json()
                token = data.get("token")
                
                if token:
                    tenant.shiprocket_token = token
                    # Tokens usually valid for 10 days, we'll set expire to 9 days to be safe
                    tenant.shiprocket_token_expires = now + timedelta(days=9)
                    await db.commit()
                    return token
        except httpx.HTTPError as e:
            logger.error(f"Shiprocket auth failed: {e}")
            return None

    @staticmethod
    async def get_rates(
        db: AsyncSession,
        tenant: Tenant,
        pickup_pincode: str,
        delivery_pincode: str,
        weight: float = 1.0,
        cod: int = 0
    ) -> List[Dict[str, Any]]:
        token = await ShiprocketService.get_valid_token(db, tenant)
        if not token:
            logger.warning("Shiprocket token not available.")
            return []

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{ShiprocketService.BASE_URL}/courier/serviceability/",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "pickup_postcode": pickup_pincode,
                        "delivery_postcode": delivery_pincode,
                        "weight": weight,
                        "cod": cod
                    }
                )
                res.raise_for_status()
                data = res.json()
                
                couriers = data.get("data", {}).get("available_courier_companies", [])
                if not couriers:
                    return []
                    
                sorted_by_price = sorted(couriers, key=lambda x: x.get("rate", 0))
                sorted_by_time = sorted(couriers, key=lambda x: x.get("estimated_delivery_days", 99))
                
                cheapest = sorted_by_price[0]
                fastest = sorted_by_time[0]
                
                results = []
                results.append({
                    "service_name": "Standard",
                    "delivery_fee": Decimal(str(cheapest.get("rate", 0))),
                    "estimated_days": int(cheapest.get("estimated_delivery_days", 5))
                })
                
                # Only add express if it's actually faster and different
                if fastest["id"] != cheapest["id"] and fastest.get("estimated_delivery_days", 99) < cheapest.get("estimated_delivery_days", 99):
                    results.append({
                        "service_name": "Express",
                        "delivery_fee": Decimal(str(fastest.get("rate", 0))),
                        "estimated_days": int(fastest.get("estimated_delivery_days", 2))
                    })
                
                return results

        except httpx.HTTPError as e:
            logger.error(f"Shiprocket get_rates failed: {e}")
            return []

shiprocket_service = ShiprocketService()
