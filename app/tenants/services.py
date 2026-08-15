import uuid
from typing import Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.tenants.models import Tenant, TenantDomain, SystemDomain
from app.users.models import User
from app.utils.audit import log_audit_event
from app.auth.services import auth_service
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

class TenantService:
    """Service handling PostgreSQL and MongoDB operations for multi-tenant organizations."""

    @staticmethod
    async def create_tenant(
        db: AsyncSession,
        business_name: str,
        admin_name: str,
        admin_email: Optional[str],
        admin_mobile: str,
        admin_password: Optional[str]
    ) -> Tenant:
        """Register a new Tenant and its initial Tenant Administrator."""
        # Check if Tenant already exists
        stmt = select(Tenant).where(Tenant.business_name == business_name)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError(f"Tenant with business name '{business_name}' already exists.")

        # Create the Tenant record
        tenant = Tenant(business_name=business_name)
        db.add(tenant)
        await db.flush()  # Populates tenant.id without committing yet

        # Create Admin User under the Tenant
        hashed_password = auth_service.hash_password(admin_password) if admin_password else None
        admin_user = User(
            name=admin_name,
            mobilenumber=admin_mobile,
            email=admin_email,
            password=hashed_password,
            role="TENANT_ADMIN",
            tenant_id=tenant.id,
            status="ACTIVE"
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(tenant)

        # Log action to MongoDB safely
        await log_audit_event(
            action="TENANT_REGISTERED",
            tenant_id=str(tenant.id),
            user_id=str(admin_user.id),
            details={
                "business_name": business_name,
                "admin_name": admin_name,
                "admin_email": admin_email,
                "admin_mobile": admin_mobile
            }
        )

        return tenant

    @staticmethod
    async def get_tenant_by_id(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Fetch tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_tenant(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        business_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        favicon_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        theme_name: Optional[str] = None,
        contact_telephone: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        support_email: Optional[str] = None,
        gstin_code: Optional[str] = None,
        currency: Optional[str] = None,
        shiprocket_email: Optional[str] = None,
        shiprocket_password: Optional[str] = None,
        payment_public_key: Optional[str] = None,
        payment_secret_key: Optional[str] = None,
        payment_sandbox_mode: Optional[bool] = None
    ) -> Tenant:
        """Update Tenant branding and details."""
        tenant = await TenantService.get_tenant_by_id(db, tenant_id)
        if not tenant:
            from app.utils.exceptions import NotFoundError
            raise NotFoundError(f"Tenant not found.")

        if business_name is not None:
            tenant.business_name = business_name
        if logo_url is not None:
            tenant.logo_url = logo_url
        if favicon_url is not None:
            tenant.favicon_url = favicon_url
        if primary_color is not None:
            tenant.primary_color = primary_color
        if secondary_color is not None:
            tenant.secondary_color = secondary_color
        if theme_name is not None:
            tenant.theme_name = theme_name
        if contact_telephone is not None:
            tenant.contact_telephone = contact_telephone
        if whatsapp_number is not None:
            tenant.whatsapp_number = whatsapp_number
        if support_email is not None:
            tenant.support_email = support_email
        if gstin_code is not None:
            tenant.gstin_code = gstin_code
        if currency is not None:
            tenant.currency = currency
        if shiprocket_email is not None:
            tenant.shiprocket_email = shiprocket_email
        if shiprocket_password is not None:
            from app.utils.security import encrypt_password
            tenant.shiprocket_password = encrypt_password(shiprocket_password)
            tenant.shiprocket_token = None
            tenant.shiprocket_token_expires = None
        if payment_public_key is not None:
            tenant.payment_public_key = payment_public_key
        if payment_secret_key is not None:
            from app.utils.security import encrypt_password
            tenant.payment_secret_key = encrypt_password(payment_secret_key)
        if payment_sandbox_mode is not None:
            tenant.payment_sandbox_mode = payment_sandbox_mode

        await db.commit()
        await db.refresh(tenant)
        return tenant


class TenantDomainService:
    """Service to resolve tenant context based on custom host domains."""

    @staticmethod
    async def get_tenant_id_by_domain(db: AsyncSession, domain: str) -> Optional[uuid.UUID]:
        """
        Resolves the tenant UUID associated with the given domain host.
        Returns None if the domain is a registered system domain or if no mapping exists.
        """
        if not domain:
            return None

        # Normalize to lowercase
        domain = domain.lower()

        # 1. Check if the domain is registered as a system-level domain
        system_stmt = select(SystemDomain).where(SystemDomain.domain == domain)
        system_res = await db.execute(system_stmt)
        if system_res.scalar_one_or_none():
            logger.debug(f"Domain '{domain}' is registered as a system domain. Skipping tenant lookup.")
            return None

        # 2. Check if the domain is mapped to a tenant
        domain_stmt = select(TenantDomain.tenant_id).where(TenantDomain.domain == domain)
        domain_res = await db.execute(domain_stmt)
        tenant_id = domain_res.scalar_one_or_none()

        if tenant_id:
            logger.info(f"Resolved domain '{domain}' to tenant ID {tenant_id}")
            return tenant_id

        logger.debug(f"Domain '{domain}' is not mapped to any tenant or system domain.")
        return None

tenant_service = TenantService()
tenant_domain_service = TenantDomainService()
