import uuid
from datetime import datetime
from typing import Optional, Annotated
import strawberry

from app.referral.models import (
    UserReferral as DBUserReferral,
    UserReferralHistory as DBUserReferralHistory,
    UserReferralPointsTransactionHistory as DBUserReferralPointsTransactionHistory
)
from app.referral.services import referral_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class UserReferralType:
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    referral_points: float = strawberry.field(name="referralPoints")
    referral_code: str = strawberry.field(name="referralCode")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def histories(self, info: strawberry.Info) -> list["UserReferralHistoryType"]:
        db = info.context.db
        from sqlalchemy.future import select
        from app.referral.models import UserReferralHistory
        stmt = select(UserReferralHistory).where(UserReferralHistory.referrer_user_id == self.user_id).order_by(UserReferralHistory.created_at.desc())
        res = await db.execute(stmt)
        db_hist = res.scalars().all()
        return [UserReferralHistoryType(h) for h in db_hist]

    @strawberry.field
    async def transactions(self, info: strawberry.Info) -> list["UserReferralPointsTransactionHistoryType"]:
        db = info.context.db
        from sqlalchemy.future import select
        from app.referral.models import UserReferralPointsTransactionHistory
        stmt = select(UserReferralPointsTransactionHistory).where(UserReferralPointsTransactionHistory.user_referral_id == self.id).order_by(UserReferralPointsTransactionHistory.created_at.desc())
        res = await db.execute(stmt)
        db_txs = res.scalars().all()
        return [UserReferralPointsTransactionHistoryType(tx) for tx in db_txs]

    def __init__(self, db_ref: DBUserReferral):
        self.id = db_ref.id
        self.user_id = db_ref.user_id
        self.referral_points = float(db_ref.referral_points)
        self.referral_code = db_ref.referral_code
        self.created_at = db_ref.created_at
        self.updated_at = db_ref.updated_at


@strawberry.type
class UserReferralHistoryType:
    id: uuid.UUID
    referral_user_id: uuid.UUID = strawberry.field(name="referralUserId")
    referrer_user_id: uuid.UUID = strawberry.field(name="referrerUserId")
    referred_entity: str = strawberry.field(name="referredEntity")
    referred_entity_id: Optional[uuid.UUID] = strawberry.field(name="referredEntityId")
    points: float
    created_at: datetime = strawberry.field(name="createdAt")

    @strawberry.field
    async def referral_user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        db = info.context.db
        from app.users.services import user_service
        db_user = await user_service.get_user_by_id(db, self.referral_user_id)
        if not db_user:
            return None
        from app.users.graphql import UserType
        return UserType(db_user)

    @strawberry.field
    async def referrer_user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        db = info.context.db
        from app.users.services import user_service
        db_user = await user_service.get_user_by_id(db, self.referrer_user_id)
        if not db_user:
            return None
        from app.users.graphql import UserType
        return UserType(db_user)

    def __init__(self, db_hist: DBUserReferralHistory):
        self.id = db_hist.id
        self.referral_user_id = db_hist.referral_user_id
        self.referrer_user_id = db_hist.referrer_user_id
        self.referred_entity = db_hist.referred_entity
        self.referred_entity_id = db_hist.referred_entity_id
        self.points = float(db_hist.points)
        self.created_at = db_hist.created_at


@strawberry.type
class UserReferralPointsTransactionHistoryType:
    id: uuid.UUID
    user_referral_id: uuid.UUID = strawberry.field(name="userReferralId")
    wallet_id: uuid.UUID = strawberry.field(name="walletId")
    points: float
    type: str
    payment_id: Optional[uuid.UUID] = strawberry.field(name="paymentId")
    order_id: Optional[uuid.UUID] = strawberry.field(name="orderId")
    remarks: Optional[str]
    created_at: datetime = strawberry.field(name="createdAt")

    def __init__(self, db_tx: DBUserReferralPointsTransactionHistory):
        self.id = db_tx.id
        self.user_referral_id = db_tx.user_referral_id
        self.wallet_id = db_tx.wallet_id
        self.points = float(db_tx.points)
        self.type = db_tx.type
        self.payment_id = db_tx.payment_id
        self.order_id = db_tx.order_id
        self.remarks = db_tx.remarks
        self.created_at = db_tx.created_at


@strawberry.input
class ClaimReferralInput:
    referrer_code: str = strawberry.field(name="referrerCode")
    referred_entity: str = strawberry.field(name="referredEntity")
    referred_entity_id: Optional[uuid.UUID] = strawberry.field(default=None, name="referredEntityId")
    points: float
    payment_id: Optional[uuid.UUID] = strawberry.field(default=None, name="paymentId")
    order_id: Optional[uuid.UUID] = strawberry.field(default=None, name="orderId")
    remarks: Optional[str] = strawberry.field(default=None)


@strawberry.type
class ReferralQuery:
    @strawberry.field
    async def my_referral(self, info: strawberry.Info) -> Optional[UserReferralType]:
        """Fetch referral info of the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        from sqlalchemy.future import select
        from app.referral.models import UserReferral
        stmt = select(UserReferral).where(UserReferral.user_id == current_user.id)
        res = await db.execute(stmt)
        db_ref = res.scalar_one_or_none()
        return UserReferralType(db_ref) if db_ref else None


@strawberry.type
class ReferralMutation:
    @strawberry.mutation
    async def generate_referral_code(
        self,
        info: strawberry.Info,
        custom_code: Optional[str] = None
    ) -> UserReferralType:
        """Register or retrieve custom referral code configuration for the authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_ref = await referral_service.generate_referral_code(
            db=db,
            user_id=current_user.id,
            custom_code=custom_code
        )
        return UserReferralType(db_ref)

    @strawberry.mutation
    async def claim_referral(
        self,
        info: strawberry.Info,
        input: ClaimReferralInput
    ) -> UserReferralHistoryType:
        """Claim referral points for the authenticated user using referrer's code."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_hist = await referral_service.claim_referral(
            db=db,
            referral_user_id=current_user.id,
            referrer_code=input.referrer_code,
            referred_entity=input.referred_entity,
            referred_entity_id=input.referred_entity_id,
            points=input.points,
            payment_id=input.payment_id,
            order_id=input.order_id,
            remarks=input.remarks
        )
        return UserReferralHistoryType(db_hist)
