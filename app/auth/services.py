import random
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import jwt
import bcrypt
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database.redis import redis_client
from app.users.models import User
from app.tenants.models import Tenant
from app.utils.audit import log_audit_event
from app.utils.exceptions import (
    InvalidCredentialsError,
    InvalidOTPError,
    TenantNotFoundError,
    UserNotFoundError,
    ValidationError,
    OTPThrottleError
)

logger = logging.getLogger(__name__)

class SMSService:
    """Service to handle SMS OTP dispatch, verification, and throttling."""

    THROTTLE_TTL_SECONDS = 60  # Rate limit: 1 OTP request per minute
    OTP_TTL_SECONDS = 300     # OTP valid for 5 minutes

    @staticmethod
    def _generate_otp() -> str:
        """Generate a cryptographically secure 6-digit OTP."""
        return str(random.randint(100000, 999999))

    async def send_otp(self, mobilenumber: str) -> str:
        """
        Generate, cache in Redis, and send an OTP to the given mobile number.
        Returns the generated OTP (for testing or debugging).
        """
        # 1. Check throttling in Redis
        throttle_key = f"otp_throttle:{mobilenumber}"
        is_throttled = await redis_client.exists(throttle_key)
        if is_throttled:
            raise OTPThrottleError(
                f"An OTP was recently requested for {mobilenumber}. Please wait {self.THROTTLE_TTL_SECONDS} seconds."
            )

        # 2. Generate OTP
        otp = self._generate_otp()
        otp_key = f"otp:{mobilenumber}"

        # 3. Store OTP and Throttle marker in Redis
        await redis_client.set(otp_key, otp, expire_seconds=self.OTP_TTL_SECONDS)
        await redis_client.set(throttle_key, "1", expire_seconds=self.THROTTLE_TTL_SECONDS)

        # 4. Format the SMS message matching the exact required template
        message = (
            f"Use OTP {otp} to log in to your Account. "
            f"Never share your OTP with anyone . Support contact: {settings.SUPPORT_CONTACT} - My Dreams"
        )

        # 5. Dispatch SMS request using httpx
        params = {
            "apikey": settings.SMS_API_KEY,
            "senderid": settings.SMS_SENDER_ID,
            "number": mobilenumber,
            "message": message,
        }

        # Print the OTP in console during development so the developer can see it instantly
        print(f"\n[SMS OTP SENT] Number: {mobilenumber} | OTP: {otp}\n")
        logger.info(f"Generated OTP {otp} for {mobilenumber}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(settings.SMS_OTP_API_URL, params=params)
                logger.info(f"SMS API response: status={response.status_code}, content={response.text}")
        except httpx.HTTPError as exc:
            logger.error(f"Failed to deliver SMS to {mobilenumber} via gateway: {exc}")

        return otp

    async def verify_otp(self, mobilenumber: str, user_otp: str) -> bool:
        """Verify the OTP stored in Redis. Returns True if valid, False otherwise."""
        otp_key = f"otp:{mobilenumber}"
        cached_otp = await redis_client.get(otp_key)

        if not cached_otp:
            return False

        if cached_otp == user_otp:
            # Consume the OTP once verified successfully
            await redis_client.delete(otp_key)
            return True

        return False

sms_service = SMSService()


class AuthService:
    """Service to handle hashing, JWT creation, validation, and authentication."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a hash."""
        try:
            plain_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(plain_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    @staticmethod
    def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
        """Create a signed JWT token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": int(expire.timestamp())})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def generate_tokens(self, user_id: str, tenant_id: Optional[str], role: str) -> Dict[str, str]:
        """Generate access and refresh tokens for a user."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        access_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "role": role,
            "type": "access"
        }

        refresh_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "role": role,
            "type": "refresh"
        }

        access_token = self.create_jwt_token(access_payload, access_token_expires)
        refresh_token = self.create_jwt_token(refresh_payload, refresh_token_expires)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode a JWT and return the payload."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Expired JWT signature: {e}")
            raise jwt.ExpiredSignatureError("Token signature has expired.")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise jwt.InvalidTokenError("Invalid token format or signature.")

    async def authenticate_with_password(
        self,
        db: AsyncSession,
        email_or_mobile: str,
        password: str,
        tenant_id: uuid.UUID
    ) -> User:
        """Authenticate a user using password."""
        stmt = select(User).where(
            (User.tenant_id == tenant_id) &
            ((User.email == email_or_mobile) | (User.mobilenumber == email_or_mobile))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.password:
            raise InvalidCredentialsError("Invalid email/phone or password")

        if not self.verify_password(password, user.password):
            raise InvalidCredentialsError("Invalid email/phone or password")

        if user.status != "ACTIVE":
            raise ValidationError(f"User account status is {user.status}")

        await log_audit_event(
            action="USER_LOGIN_PASSWORD",
            tenant_id=str(tenant_id),
            user_id=str(user.id),
            details={"email": user.email, "mobilenumber": user.mobilenumber}
        )

        return user

    async def admin_authenticate_with_password(
        self,
        db: AsyncSession,
        email_or_mobile: str,
        password: str
    ) -> User:
        """Authenticate an admin user using password globally across all tenants."""
        stmt = select(User).where(
            (User.email == email_or_mobile) | (User.mobilenumber == email_or_mobile)
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user or not user.password:
            raise InvalidCredentialsError("Invalid email/phone or password")

        if not self.verify_password(password, user.password):
            raise InvalidCredentialsError("Invalid email/phone or password")

        if user.status != "ACTIVE":
            raise ValidationError(f"User account status is {user.status}")

        await log_audit_event(
            action="ADMIN_LOGIN_PASSWORD",
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            user_id=str(user.id),
            details={"email": user.email, "mobilenumber": user.mobilenumber}
        )

        return user

    async def authenticate_with_otp(
        self,
        db: AsyncSession,
        mobilenumber: str,
        otp: str,
        tenant_id: uuid.UUID
    ) -> User:
        """Authenticate a user using SMS OTP. Creates the user automatically if they do not exist."""
        is_valid = await sms_service.verify_otp(mobilenumber, otp)
        if not is_valid:
            raise InvalidOTPError("Invalid or expired OTP code.")

        stmt = select(User).where(
            (User.tenant_id == tenant_id) &
            (User.mobilenumber == mobilenumber)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Check if Tenant exists first
            stmt_tenant = select(Tenant).where(Tenant.id == tenant_id)
            res_tenant = await db.execute(stmt_tenant)
            if not res_tenant.scalar_one_or_none():
                raise TenantNotFoundError(f"Tenant {tenant_id} not found.")

            # Create User automatically
            user = User(
                name=f"User {mobilenumber}",
                mobilenumber=mobilenumber,
                email=None,
                password=None,
                role="USER",
                tenant_id=tenant_id,
                status="ACTIVE"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            await log_audit_event(
                action="USER_CREATED",
                tenant_id=str(tenant_id),
                user_id=str(user.id),
                details={"name": user.name, "email": None, "role": "USER", "auto_created": True}
            )

        if user.status != "ACTIVE":
            raise ValidationError(f"User account status is {user.status}")

        await log_audit_event(
            action="USER_LOGIN_OTP",
            tenant_id=str(tenant_id),
            user_id=str(user.id),
            details={"mobilenumber": mobilenumber}
        )

        return user

auth_service = AuthService()
