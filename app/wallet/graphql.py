import uuid
from datetime import datetime
from typing import Optional
import strawberry

from app.wallet.models import (
    UserWallet as DBUserWallet,
    UserWalletTransaction as DBUserWalletTransaction
)
from app.wallet.services import wallet_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class UserWalletType:
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    points: float
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def transactions(self, info: strawberry.Info) -> list["UserWalletTransactionType"]:
        db = info.context.db
        from sqlalchemy.future import select
        from app.wallet.models import UserWalletTransaction
        stmt = select(UserWalletTransaction).where(UserWalletTransaction.wallet_id == self.id).order_by(UserWalletTransaction.created_at.desc())
        res = await db.execute(stmt)
        db_txs = res.scalars().all()
        return [UserWalletTransactionType(tx) for tx in db_txs]

    def __init__(self, db_wallet: DBUserWallet):
        self.id = db_wallet.id
        self.user_id = db_wallet.user_id
        self.points = float(db_wallet.points)
        self.created_at = db_wallet.created_at
        self.updated_at = db_wallet.updated_at


@strawberry.type
class UserWalletTransactionType:
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    wallet_id: uuid.UUID = strawberry.field(name="walletId")
    points: float
    type: str
    payment_id: Optional[uuid.UUID] = strawberry.field(name="paymentId")
    order_id: Optional[uuid.UUID] = strawberry.field(name="orderId")
    remarks: Optional[str]
    created_at: datetime = strawberry.field(name="createdAt")

    def __init__(self, db_tx: DBUserWalletTransaction):
        self.id = db_tx.id
        self.user_id = db_tx.user_id
        self.wallet_id = db_tx.wallet_id
        self.points = float(db_tx.points)
        self.type = db_tx.type
        self.payment_id = db_tx.payment_id
        self.order_id = db_tx.order_id
        self.remarks = db_tx.remarks
        self.created_at = db_tx.created_at


@strawberry.type
class WalletQuery:
    @strawberry.field
    async def my_wallet(self, info: strawberry.Info) -> UserWalletType:
        """Fetch wallet of the currently authenticated user."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_wallet = await wallet_service.get_or_create_wallet(db, current_user.id)
        return UserWalletType(db_wallet)


@strawberry.type
class WalletMutation:
    @strawberry.mutation
    async def credit_wallet(
        self,
        info: strawberry.Info,
        user_id: uuid.UUID,
        points: float,
        remarks: Optional[str] = None
    ) -> UserWalletTransactionType:
        """Credit points to a user's wallet (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to transact wallets.")
        
        db = info.context.db
        db_tx = await wallet_service.transact_wallet(
            db=db,
            user_id=user_id,
            points=points,
            transaction_type="CREDIT",
            remarks=remarks,
            actor_user=current_user
        )
        return UserWalletTransactionType(db_tx)

    @strawberry.mutation
    async def debit_wallet(
        self,
        info: strawberry.Info,
        user_id: uuid.UUID,
        points: float,
        remarks: Optional[str] = None
    ) -> UserWalletTransactionType:
        """Debit points from a user's wallet (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to transact wallets.")
        
        db = info.context.db
        db_tx = await wallet_service.transact_wallet(
            db=db,
            user_id=user_id,
            points=points,
            transaction_type="DEBIT",
            remarks=remarks,
            actor_user=current_user
        )
        return UserWalletTransactionType(db_tx)
