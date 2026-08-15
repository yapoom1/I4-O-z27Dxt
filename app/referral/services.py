import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.referral.models import (
    UserReferral,
    UserReferralHistory,
    UserReferralPointsTransactionHistory
)
from app.wallet.models import UserWalletTransaction
from app.wallet.services import wallet_service
from app.users.models import User
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class ReferralService:
    """Service handling user referrals configuration and claiming rewards."""

    @staticmethod
    async def generate_referral_code(
        db: AsyncSession,
        user_id: uuid.UUID,
        custom_code: Optional[str] = None
    ) -> UserReferral:
        """Register or retrieve a user's custom referral code configuration."""
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            raise ValidationError("User not found.")

        # Check if already exists
        stmt = select(UserReferral).where(UserReferral.user_id == user_id)
        res = await db.execute(stmt)
        referral = res.scalar_one_or_none()

        if referral:
            if custom_code and custom_code != referral.referral_code:
                raise ValidationError("User already has a registered referral code.")
            return referral

        # Generate unique code if not provided
        if not custom_code:
            custom_code = f"REF-{user_id.hex[:6].upper()}"
        else:
            custom_code = custom_code.strip().upper()
            if not custom_code:
                raise ValidationError("Referral code cannot be empty.")
            
            # Check uniqueness
            stmt = select(UserReferral).where(UserReferral.referral_code == custom_code)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                raise ValidationError(f"Referral code '{custom_code}' is already taken.")

        referral = UserReferral(
            user_id=user_id,
            referral_points=0.00,
            referral_code=custom_code
        )
        db.add(referral)
        await db.commit()
        await db.refresh(referral)

        await log_audit_event(
            action="REFERRAL_CODE_GENERATED",
            tenant_id=None,
            user_id=str(user_id),
            details={
                "referral_id": str(referral.id),
                "referral_code": custom_code
            }
        )

        return referral

    @staticmethod
    async def claim_referral(
        db: AsyncSession,
        referral_user_id: uuid.UUID, # referred customer (new user)
        referrer_code: str,          # code of the referring user
        referred_entity: str,        # USER, PRODUCT, ORDER
        referred_entity_id: Optional[uuid.UUID],
        points: float,
        payment_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None
    ) -> UserReferralHistory:
        """Process referral claims, award points to the referrer, and update wallet balances."""
        if points <= 0:
            raise ValidationError("Referral points must be positive.")

        referred_entity = referred_entity.upper()
        if referred_entity not in ["USER", "PRODUCT", "ORDER"]:
            raise ValidationError("Referred entity must be USER, PRODUCT, or ORDER.")

        # Find referrer
        stmt = select(UserReferral).where(UserReferral.referral_code == referrer_code.strip().upper())
        res = await db.execute(stmt)
        referrer_referral = res.scalar_one_or_none()
        if not referrer_referral:
            raise ValidationError(f"Referral code '{referrer_code}' does not exist.")

        referrer_user_id = referrer_referral.user_id
        if referrer_user_id == referral_user_id:
            raise ValidationError("You cannot refer yourself.")

        # Prevent double-referral of the same user
        stmt = select(UserReferralHistory).where(
            (UserReferralHistory.referral_user_id == referral_user_id) &
            (UserReferralHistory.referred_entity == "USER")
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ValidationError("Referred user has already been referred previously.")

        # 1. Log referral history
        history = UserReferralHistory(
            referral_user_id=referral_user_id,
            referrer_user_id=referrer_user_id,
            referred_entity=referred_entity,
            referred_entity_id=referred_entity_id,
            points=points
        )
        db.add(history)

        # 2. Update referrer's UserReferral points accumulation field
        referrer_referral.referral_points = float(referrer_referral.referral_points) + points

        # 3. Credit referrer's loyalty wallet
        wallet = await wallet_service.get_or_create_wallet(db, referrer_user_id)
        
        # Log to UserWalletTransaction
        wallet_transaction = UserWalletTransaction(
            user_id=referrer_user_id,
            wallet_id=wallet.id,
            points=points,
            type="CREDIT",
            payment_id=payment_id,
            order_id=order_id,
            remarks=remarks or f"Referral points award for referring entity {referred_entity}"
        )
        db.add(wallet_transaction)

        # Update wallet points
        wallet.points = float(wallet.points) + points

        # 4. Log to UserReferralPointsTransactionHistory
        ref_transaction = UserReferralPointsTransactionHistory(
            user_referral_id=referrer_referral.id,
            wallet_id=wallet.id,
            points=points,
            type="CREDIT",
            payment_id=payment_id,
            order_id=order_id,
            remarks=remarks or f"Referral reward points credited"
        )
        db.add(ref_transaction)

        await db.commit()
        await db.refresh(history)

        await log_audit_event(
            action="REFERRAL_CLAIMED",
            tenant_id=None,
            user_id=str(referrer_user_id),
            details={
                "referral_history_id": str(history.id),
                "referrer_code": referrer_code,
                "referred_user_id": str(referral_user_id),
                "points": str(points)
            }
        )

        return history

referral_service = ReferralService()
