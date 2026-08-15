import uuid
from typing import Optional
import strawberry
import jwt

from app.auth.services import auth_service, sms_service
from app.users.services import user_service
from app.users.graphql import UserType
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError, UnauthorizedError, UserNotFoundError

@strawberry.type
class AuthTokensType:
    """Access and Refresh token packet."""
    @strawberry.field(name="accessToken")
    def access_token(self) -> str:
        return self._tokens.get("access_token")

    @strawberry.field(name="refreshToken")
    def refresh_token(self) -> str:
        return self._tokens.get("refresh_token")

    @strawberry.field(name="tokenType")
    def token_type(self) -> str:
        return self._tokens.get("token_type", "bearer")

    def __init__(self, tokens: dict):
        self._tokens = tokens


@strawberry.type
class AuthPayload:
    """Payload returned on successful authentication."""
    tokens: AuthTokensType
    user: UserType


@strawberry.type
class SendOtpResult:
    """Response returned after attempting to send an OTP."""
    success: bool
    message: str
    otp: Optional[str] = None


@strawberry.type
class AuthMutation:
    @strawberry.mutation
    async def send_otp(self, info: strawberry.Info, mobilenumber: str) -> SendOtpResult:
        """Generate and dispatch an SMS OTP. Throttled to 1 request per minute."""
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant context missing. Please provide X-Tenant-ID header.")

        otp = await sms_service.send_otp(mobilenumber)
        
        await log_audit_event(
            action="OTP_DISPATCHED",
            tenant_id=str(tenant_id),
            details={"mobilenumber": mobilenumber}
        )

        return SendOtpResult(
            success=True,
            message="OTP sent successfully.",
            otp=otp
        )

    @strawberry.mutation
    async def login_with_otp(self, info: strawberry.Info, mobilenumber: str, otp: str) -> AuthPayload:
        """Authenticate user using mobile number and SMS OTP code."""
        db = info.context.db
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant context missing. Please provide X-Tenant-ID header.")

        db_user = await auth_service.authenticate_with_otp(
            db=db,
            mobilenumber=mobilenumber,
            otp=otp,
            tenant_id=tenant_id
        )

        tokens = auth_service.generate_tokens(
            user_id=str(db_user.id),
            tenant_id=str(tenant_id),
            role=db_user.role
        )

        return AuthPayload(
            tokens=AuthTokensType(tokens),
            user=UserType(db_user)
        )

    @strawberry.mutation
    async def login_with_password(self, info: strawberry.Info, email_or_mobile: str, password: str) -> AuthPayload:
        """Authenticate user using email/mobile and plaintext password."""
        db = info.context.db
        tenant_id = info.context.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant context missing. Please provide X-Tenant-ID header.")

        db_user = await auth_service.authenticate_with_password(
            db=db,
            email_or_mobile=email_or_mobile,
            password=password,
            tenant_id=tenant_id
        )

        tokens = auth_service.generate_tokens(
            user_id=str(db_user.id),
            tenant_id=str(tenant_id),
            role=db_user.role
        )

        return AuthPayload(
            tokens=AuthTokensType(tokens),
            user=UserType(db_user)
        )

    @strawberry.mutation
    async def admin_login_with_password(self, info: strawberry.Info, email_or_mobile: str, password: str) -> AuthPayload:
        """Authenticate admin globally without a tenant context and fetch their tenant ID."""
        db = info.context.db

        db_user = await auth_service.admin_authenticate_with_password(
            db=db,
            email_or_mobile=email_or_mobile,
            password=password
        )

        tokens = auth_service.generate_tokens(
            user_id=str(db_user.id),
            tenant_id=str(db_user.tenant_id) if db_user.tenant_id else None,
            role=db_user.role
        )

        return AuthPayload(
            tokens=AuthTokensType(tokens),
            user=UserType(db_user)
        )

    @strawberry.mutation
    async def refresh_token(self, info: strawberry.Info, refresh_token: str) -> AuthTokensType:
        """Exchange a valid JWT refresh token for new access and refresh tokens."""
        db = info.context.db
        try:
            payload = auth_service.decode_token(refresh_token)
        except jwt.PyJWTError as e:
            raise UnauthorizedError(f"Invalid or expired refresh token: {str(e)}")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Token is not a refresh token.")

        user_id_str = payload.get("sub")
        tenant_id_str = payload.get("tenant_id")
        if not user_id_str or not tenant_id_str:
            raise UnauthorizedError("Invalid token payload structure.")

        user_id = uuid.UUID(user_id_str)
        tenant_id = uuid.UUID(tenant_id_str)
        db_user = await user_service.get_user_by_id(db, user_id, tenant_id)
        if not db_user:
            raise UserNotFoundError("User associated with token does not exist in this tenant.")

        if db_user.status != "ACTIVE":
            raise ValidationError(f"User account status is {db_user.status}")

        tokens = auth_service.generate_tokens(
            user_id=str(db_user.id),
            tenant_id=str(db_user.tenant_id) if db_user.tenant_id else None,
            role=db_user.role
        )

        await log_audit_event(
            action="TOKEN_REFRESHED",
            tenant_id=str(db_user.tenant_id) if db_user.tenant_id else None,
            user_id=str(db_user.id)
        )

        return AuthTokensType(tokens)
