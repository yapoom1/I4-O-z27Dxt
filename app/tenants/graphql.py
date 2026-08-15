import uuid
from datetime import datetime
from typing import Optional
import strawberry

from app.tenants.models import Tenant as DBTenant
from app.tenants.services import tenant_service

@strawberry.type
class TenantType:
    """GraphQL representation of a Tenant."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @strawberry.field(name="businessName")
    def business_name(self) -> str:
        return self._db_tenant.business_name

    @strawberry.field(name="logoUrl")
    def logo_url(self) -> Optional[str]:
        return self._db_tenant.logo_url

    @strawberry.field(name="faviconUrl")
    def favicon_url(self) -> Optional[str]:
        return self._db_tenant.favicon_url

    @strawberry.field(name="primaryColor")
    def primary_color(self) -> Optional[str]:
        return self._db_tenant.primary_color

    @strawberry.field(name="secondaryColor")
    def secondary_color(self) -> Optional[str]:
        return self._db_tenant.secondary_color

    @strawberry.field(name="themeName")
    def theme_name(self) -> Optional[str]:
        return self._db_tenant.theme_name

    @strawberry.field(name="shiprocketEmail")
    def shiprocket_email(self) -> Optional[str]:
        return self._db_tenant.shiprocket_email

    @strawberry.field(name="contactTelephone")
    def contact_telephone(self) -> Optional[str]:
        return self._db_tenant.contact_telephone

    @strawberry.field(name="whatsappNumber")
    def whatsapp_number(self) -> Optional[str]:
        return self._db_tenant.whatsapp_number

    @strawberry.field(name="supportEmail")
    def support_email(self) -> Optional[str]:
        return self._db_tenant.support_email

    @strawberry.field(name="gstinCode")
    def gstin_code(self) -> Optional[str]:
        return self._db_tenant.gstin_code

    @strawberry.field(name="currency")
    def currency(self) -> str:
        return self._db_tenant.currency or "INR"

    @strawberry.field(name="paymentPublicKey")
    def payment_public_key(self) -> Optional[str]:
        return self._db_tenant.payment_public_key

    @strawberry.field(name="paymentSandboxMode")
    def payment_sandbox_mode(self) -> bool:
        return self._db_tenant.payment_sandbox_mode if self._db_tenant.payment_sandbox_mode is not None else True

    def __init__(self, db_tenant: DBTenant):
        self.id = db_tenant.id
        self.created_at = db_tenant.created_at
        self.updated_at = db_tenant.updated_at
        self._db_tenant = db_tenant


@strawberry.input
class CreateTenantInput:
    business_name: str = strawberry.field(name="businessName")
    admin_name: str = strawberry.field(name="adminName")
    admin_email: Optional[str] = strawberry.field(default=None, name="adminEmail")
    admin_mobile: str = strawberry.field(name="adminMobile")
    admin_password: Optional[str] = strawberry.field(default=None, name="adminPassword")


@strawberry.type
class TenantQuery:
    @strawberry.field
    async def tenant(self, info: strawberry.Info) -> Optional[TenantType]:
        """Fetch details of the active tenant from context or authenticated user."""
        tenant_id = info.context.tenant_id
        if not tenant_id and info.context.user:
            tenant_id = info.context.user.tenant_id

        if not tenant_id:
            from app.utils.exceptions import UnauthorizedError
            raise UnauthorizedError("Tenant context is missing. Provide X-Tenant-ID header.")

        db_tenant = await tenant_service.get_tenant_by_id(info.context.db, tenant_id)
        if not db_tenant:
            return None

        return TenantType(db_tenant)

@strawberry.input
class UpdateTenantInput:
    business_name: Optional[str] = strawberry.field(default=None, name="businessName")
    logo_url: Optional[str] = strawberry.field(default=None, name="logoUrl")
    favicon_url: Optional[str] = strawberry.field(default=None, name="faviconUrl")
    primary_color: Optional[str] = strawberry.field(default=None, name="primaryColor")
    secondary_color: Optional[str] = strawberry.field(default=None, name="secondaryColor")
    theme_name: Optional[str] = strawberry.field(default=None, name="themeName")
    contact_telephone: Optional[str] = strawberry.field(default=None, name="contactTelephone")
    whatsapp_number: Optional[str] = strawberry.field(default=None, name="whatsappNumber")
    support_email: Optional[str] = strawberry.field(default=None, name="supportEmail")
    gstin_code: Optional[str] = strawberry.field(default=None, name="gstinCode")
    currency: Optional[str] = strawberry.field(default=None, name="currency")
    shiprocket_email: Optional[str] = strawberry.field(default=None, name="shiprocketEmail")
    shiprocket_password: Optional[str] = strawberry.field(default=None, name="shiprocketPassword")
    payment_public_key: Optional[str] = strawberry.field(default=None, name="paymentPublicKey")
    payment_secret_key: Optional[str] = strawberry.field(default=None, name="paymentSecretKey")
    payment_sandbox_mode: Optional[bool] = strawberry.field(default=None, name="paymentSandboxMode")

@strawberry.type
class TenantMutation:
    @strawberry.mutation
    async def create_tenant(self, info: strawberry.Info, input: CreateTenantInput) -> TenantType:
        """Register a new Tenant alongside its Administrator user."""
        db = info.context.db
        db_tenant = await tenant_service.create_tenant(
            db=db,
            business_name=input.business_name,
            admin_name=input.admin_name,
            admin_email=input.admin_email,
            admin_mobile=input.admin_mobile,
            admin_password=input.admin_password
        )
        return TenantType(db_tenant)

    @strawberry.mutation
    async def update_tenant(self, info: strawberry.Info, input: UpdateTenantInput) -> TenantType:
        """Update the active Tenant's branding details."""
        tenant_id = info.context.tenant_id
        if not tenant_id and info.context.user:
            tenant_id = info.context.user.tenant_id

        if not tenant_id:
            from app.utils.exceptions import UnauthorizedError
            raise UnauthorizedError("Tenant context is missing. Provide X-Tenant-ID header.")

        db = info.context.db
        db_tenant = await tenant_service.update_tenant(
            db=db,
            tenant_id=tenant_id,
            business_name=input.business_name,
            logo_url=input.logo_url,
            favicon_url=input.favicon_url,
            primary_color=input.primary_color,
            secondary_color=input.secondary_color,
            theme_name=input.theme_name,
            contact_telephone=input.contact_telephone,
            whatsapp_number=input.whatsapp_number,
            support_email=input.support_email,
            gstin_code=input.gstin_code,
            currency=input.currency,
            shiprocket_email=input.shiprocket_email,
            shiprocket_password=input.shiprocket_password,
            payment_public_key=input.payment_public_key,
            payment_secret_key=input.payment_secret_key,
            payment_sandbox_mode=input.payment_sandbox_mode
        )
        return TenantType(db_tenant)
