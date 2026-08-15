import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.reviews.models import ProductReview, OrderReview, CompanyReview
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class ReviewService:
    """Service handling PostgreSQL operations for Product, Order, and Company reviews."""

    # --- Product Review Management ---

    @staticmethod
    async def create_product_review(
        db: AsyncSession,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        rating_points: int,
        review_text: Optional[str] = None
    ) -> ProductReview:
        """Create a new pending review for a product."""
        if rating_points < 1 or rating_points > 5:
            raise ValidationError("Rating points must be an integer between 1 and 5.")

        review_record = ProductReview(
            user_id=user_id,
            product_id=product_id,
            rating_points=rating_points,
            review=review_text,
            status="PENDING"
        )
        db.add(review_record)
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="PRODUCT_REVIEW_CREATED",
            tenant_id=None,
            user_id=str(user_id),
            details={
                "review_id": str(review_record.id),
                "product_id": str(product_id),
                "rating": str(rating_points)
            }
        )

        return review_record

    @staticmethod
    async def get_product_reviews(db: AsyncSession, product_id: uuid.UUID) -> List[ProductReview]:
        """Fetch all approved reviews for a product."""
        stmt = select(ProductReview).where(
            (ProductReview.product_id == product_id) &
            (ProductReview.status == "APPROVED")
        ).order_by(ProductReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_admin_product_reviews(db: AsyncSession) -> List[ProductReview]:
        """Fetch all product reviews for administration/moderation."""
        stmt = select(ProductReview).order_by(ProductReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_product_review_status(
        db: AsyncSession,
        review_id: uuid.UUID,
        status: str,
        moderator_id: Optional[uuid.UUID] = None
    ) -> ProductReview:
        """Approve or reject a product review."""
        status = status.upper().strip()
        if status not in ["APPROVED", "REJECTED"]:
            raise ValidationError("Invalid review status. Must be APPROVED or REJECTED.")

        stmt = select(ProductReview).where(ProductReview.id == review_id)
        res = await db.execute(stmt)
        review_record = res.scalar_one_or_none()

        if not review_record:
            raise ValidationError("Product review not found.")

        review_record.status = status
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="PRODUCT_REVIEW_STATUS_UPDATED",
            tenant_id=None,
            user_id=str(moderator_id) if moderator_id else None,
            details={
                "review_id": str(review_id),
                "status": status
            }
        )

        return review_record

    # --- Order Review Management ---

    @staticmethod
    async def create_order_review(
        db: AsyncSession,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        rating_points: int,
        review_text: Optional[str] = None
    ) -> OrderReview:
        """Create a new pending review for an order."""
        if rating_points < 1 or rating_points > 5:
            raise ValidationError("Rating points must be an integer between 1 and 5.")

        review_record = OrderReview(
            user_id=user_id,
            order_id=order_id,
            rating_points=rating_points,
            review=review_text,
            status="PENDING"
        )
        db.add(review_record)
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="ORDER_REVIEW_CREATED",
            tenant_id=None,
            user_id=str(user_id),
            details={
                "review_id": str(review_record.id),
                "order_id": str(order_id),
                "rating": str(rating_points)
            }
        )

        return review_record

    @staticmethod
    async def get_order_reviews(db: AsyncSession, order_id: uuid.UUID) -> List[OrderReview]:
        """Fetch all approved reviews for an order."""
        stmt = select(OrderReview).where(
            (OrderReview.order_id == order_id) &
            (OrderReview.status == "APPROVED")
        ).order_by(OrderReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_admin_order_reviews(db: AsyncSession) -> List[OrderReview]:
        """Fetch all order reviews for administration/moderation."""
        stmt = select(OrderReview).order_by(OrderReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_order_review_status(
        db: AsyncSession,
        review_id: uuid.UUID,
        status: str,
        moderator_id: Optional[uuid.UUID] = None
    ) -> OrderReview:
        """Approve or reject an order review."""
        status = status.upper().strip()
        if status not in ["APPROVED", "REJECTED"]:
            raise ValidationError("Invalid review status. Must be APPROVED or REJECTED.")

        stmt = select(OrderReview).where(OrderReview.id == review_id)
        res = await db.execute(stmt)
        review_record = res.scalar_one_or_none()

        if not review_record:
            raise ValidationError("Order review not found.")

        review_record.status = status
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="ORDER_REVIEW_STATUS_UPDATED",
            tenant_id=None,
            user_id=str(moderator_id) if moderator_id else None,
            details={
                "review_id": str(review_id),
                "status": status
            }
        )

        return review_record

    # --- Company Review Management ---

    @staticmethod
    async def create_company_review(
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        rating_points: int,
        review_text: Optional[str] = None
    ) -> CompanyReview:
        """Create a new pending review for a company/tenant."""
        if rating_points < 1 or rating_points > 5:
            raise ValidationError("Rating points must be an integer between 1 and 5.")

        review_record = CompanyReview(
            user_id=user_id,
            tenant_id=tenant_id,
            rating_points=rating_points,
            review=review_text,
            status="PENDING"
        )
        db.add(review_record)
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="COMPANY_REVIEW_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            details={
                "review_id": str(review_record.id),
                "tenant_id": str(tenant_id),
                "rating": str(rating_points)
            }
        )

        return review_record

    @staticmethod
    async def get_company_reviews(db: AsyncSession, tenant_id: uuid.UUID) -> List[CompanyReview]:
        """Fetch all approved reviews for a company/tenant."""
        stmt = select(CompanyReview).where(
            (CompanyReview.tenant_id == tenant_id) &
            (CompanyReview.status == "APPROVED")
        ).order_by(CompanyReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_admin_company_reviews(db: AsyncSession) -> List[CompanyReview]:
        """Fetch all company reviews for administration/moderation."""
        stmt = select(CompanyReview).order_by(CompanyReview.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_company_review_status(
        db: AsyncSession,
        review_id: uuid.UUID,
        status: str,
        moderator_id: Optional[uuid.UUID] = None
    ) -> CompanyReview:
        """Approve or reject a company review."""
        status = status.upper().strip()
        if status not in ["APPROVED", "REJECTED"]:
            raise ValidationError("Invalid review status. Must be APPROVED or REJECTED.")

        stmt = select(CompanyReview).where(CompanyReview.id == review_id)
        res = await db.execute(stmt)
        review_record = res.scalar_one_or_none()

        if not review_record:
            raise ValidationError("Company review not found.")

        review_record.status = status
        await db.commit()
        await db.refresh(review_record)

        await log_audit_event(
            action="COMPANY_REVIEW_STATUS_UPDATED",
            tenant_id=None,
            user_id=str(moderator_id) if moderator_id else None,
            details={
                "review_id": str(review_id),
                "status": status
            }
        )

        return review_record

reviews_service = ReviewService()
