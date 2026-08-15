import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.wallet.models import UserWallet, UserWalletTransaction
from app.users.models import User
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError, UnauthorizedError

class WalletService:
    """Service handling PostgreSQL operations for user wallets and transactions."""

    @staticmethod
    async def get_or_create_wallet(db: AsyncSession, user_id: uuid.UUID) -> UserWallet:
        """Fetch or initialize a user's wallet points balance."""
        # Check user exists
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise ValidationError("User not found.")

        stmt = select(UserWallet).where(UserWallet.user_id == user_id)
        res = await db.execute(stmt)
        wallet = res.scalar_one_or_none()

        if not wallet:
            wallet = UserWallet(user_id=user_id, points=0.00)
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)

            await log_audit_event(
                action="WALLET_CREATED",
                tenant_id=str(user.tenant_id) if user.tenant_id else None,
                user_id=str(user_id),
                details={"wallet_id": str(wallet.id)}
            )

        return wallet

    @staticmethod
    async def transact_wallet(
        db: AsyncSession,
        user_id: uuid.UUID,
        points: float,
        transaction_type: str,
        payment_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        actor_user: Optional[User] = None
    ) -> UserWalletTransaction:
        """Perform credit/debit transactions on a user's wallet balance."""
        if points <= 0:
            raise ValidationError("Points must be a positive number.")

        transaction_type = transaction_type.upper()
        if transaction_type not in ["CREDIT", "DEBIT"]:
            raise ValidationError("Invalid transaction type. Must be CREDIT or DEBIT.")

        # Check user and tenant permissions if actor is provided
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        target_user = res.scalar_one_or_none()
        if not target_user:
            raise ValidationError("User not found.")

        if actor_user:
            if actor_user.role == "TENANT_ADMIN":
                if actor_user.tenant_id != target_user.tenant_id:
                    raise UnauthorizedError("You do not have permission to manage this user's wallet.")
            elif actor_user.role != "SUPER_ADMIN":
                raise UnauthorizedError("You do not have permission to manage user wallets.")

        wallet = await WalletService.get_or_create_wallet(db, user_id)

        if transaction_type == "DEBIT":
            if float(wallet.points) < points:
                raise ValidationError("Insufficient wallet balance.")
            wallet.points = float(wallet.points) - points
        else:
            wallet.points = float(wallet.points) + points

        transaction = UserWalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            points=points,
            type=transaction_type,
            payment_id=payment_id,
            order_id=order_id,
            remarks=remarks
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        await log_audit_event(
            action="WALLET_TRANSACTION",
            tenant_id=str(target_user.tenant_id) if target_user.tenant_id else None,
            user_id=str(user_id),
            details={
                "wallet_id": str(wallet.id),
                "transaction_id": str(transaction.id),
                "points": str(points),
                "type": transaction_type,
                "remarks": remarks
            }
        )

        return transaction

wallet_service = WalletService()
