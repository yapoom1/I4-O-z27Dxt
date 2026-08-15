import uuid
from datetime import datetime
from typing import Optional, List, Annotated
import strawberry

from app.reviews.models import (
    ProductReview as DBProductReview,
    OrderReview as DBOrderReview,
    CompanyReview as DBCompanyReview
)
from app.reviews.services import reviews_service
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class ProductReviewType:
    """GraphQL representation of a product review."""
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    product_id: uuid.UUID = strawberry.field(name="productId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str]
    status: str
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        db = info.context.db
        from app.users.services import user_service
        db_user = await user_service.get_user_by_id(db, self.user_id)
        if not db_user:
            return None
        from app.users.graphql import UserType
        return UserType(db_user)

    def __init__(self, db_review: DBProductReview):
        self.id = db_review.id
        self.user_id = db_review.user_id
        self.product_id = db_review.product_id
        self.rating_points = db_review.rating_points
        self.review = db_review.review
        self.status = db_review.status
        self.created_at = db_review.created_at
        self.updated_at = db_review.updated_at


@strawberry.type
class OrderReviewType:
    """GraphQL representation of an order review."""
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    order_id: uuid.UUID = strawberry.field(name="orderId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str]
    status: str
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        db = info.context.db
        from app.users.services import user_service
        db_user = await user_service.get_user_by_id(db, self.user_id)
        if not db_user:
            return None
        from app.users.graphql import UserType
        return UserType(db_user)

    def __init__(self, db_review: DBOrderReview):
        self.id = db_review.id
        self.user_id = db_review.user_id
        self.order_id = db_review.order_id
        self.rating_points = db_review.rating_points
        self.review = db_review.review
        self.status = db_review.status
        self.created_at = db_review.created_at
        self.updated_at = db_review.updated_at


@strawberry.type
class CompanyReviewType:
    """GraphQL representation of a company review."""
    id: uuid.UUID
    user_id: uuid.UUID = strawberry.field(name="userId")
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str]
    status: str
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Optional[Annotated["UserType", strawberry.lazy("app.users.graphql")]]:
        db = info.context.db
        from app.users.services import user_service
        db_user = await user_service.get_user_by_id(db, self.user_id)
        if not db_user:
            return None
        from app.users.graphql import UserType
        return UserType(db_user)

    def __init__(self, db_review: DBCompanyReview):
        self.id = db_review.id
        self.user_id = db_review.user_id
        self.tenant_id = db_review.tenant_id
        self.rating_points = db_review.rating_points
        self.review = db_review.review
        self.status = db_review.status
        self.created_at = db_review.created_at
        self.updated_at = db_review.updated_at


@strawberry.input
class CreateProductReviewInput:
    product_id: uuid.UUID = strawberry.field(name="productId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str] = None


@strawberry.input
class CreateOrderReviewInput:
    order_id: uuid.UUID = strawberry.field(name="orderId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str] = None


@strawberry.input
class CreateCompanyReviewInput:
    tenant_id: uuid.UUID = strawberry.field(name="tenantId")
    rating_points: int = strawberry.field(name="ratingPoints")
    review: Optional[str] = None


@strawberry.type
class ReviewQuery:
    @strawberry.field
    async def product_reviews(self, info: strawberry.Info, product_id: uuid.UUID) -> List[ProductReviewType]:
        """Fetch all approved reviews for a product."""
        db = info.context.db
        db_reviews = await reviews_service.get_product_reviews(db, product_id)
        return [ProductReviewType(r) for r in db_reviews]

    @strawberry.field
    async def order_reviews(self, info: strawberry.Info, order_id: uuid.UUID) -> List[OrderReviewType]:
        """Fetch all approved reviews for an order."""
        db = info.context.db
        db_reviews = await reviews_service.get_order_reviews(db, order_id)
        return [OrderReviewType(r) for r in db_reviews]

    @strawberry.field
    async def company_reviews(self, info: strawberry.Info, tenant_id: uuid.UUID) -> List[CompanyReviewType]:
        """Fetch all approved reviews for a company/tenant."""
        db = info.context.db
        db_reviews = await reviews_service.get_company_reviews(db, tenant_id)
        return [CompanyReviewType(r) for r in db_reviews]

    @strawberry.field
    async def admin_product_reviews(self, info: strawberry.Info) -> List[ProductReviewType]:
        """Fetch all product reviews for administration/moderation (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_reviews = await reviews_service.get_admin_product_reviews(db)
        return [ProductReviewType(r) for r in db_reviews]

    @strawberry.field
    async def admin_order_reviews(self, info: strawberry.Info) -> List[OrderReviewType]:
        """Fetch all order reviews for administration/moderation (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_reviews = await reviews_service.get_admin_order_reviews(db)
        return [OrderReviewType(r) for r in db_reviews]

    @strawberry.field
    async def admin_company_reviews(self, info: strawberry.Info) -> List[CompanyReviewType]:
        """Fetch all company reviews for administration/moderation (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_reviews = await reviews_service.get_admin_company_reviews(db)
        return [CompanyReviewType(r) for r in db_reviews]


@strawberry.type
class ReviewMutation:
    @strawberry.mutation
    async def create_product_review(self, info: strawberry.Info, input: CreateProductReviewInput) -> ProductReviewType:
        """Create a new pending review for a product."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_review = await reviews_service.create_product_review(
            db=db,
            user_id=current_user.id,
            product_id=input.product_id,
            rating_points=input.rating_points,
            review_text=input.review
        )
        return ProductReviewType(db_review)

    @strawberry.mutation
    async def create_order_review(self, info: strawberry.Info, input: CreateOrderReviewInput) -> OrderReviewType:
        """Create a new pending review for an order."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        db = info.context.db
        db_review = await reviews_service.create_order_review(
            db=db,
            user_id=current_user.id,
            order_id=input.order_id,
            rating_points=input.rating_points,
            review_text=input.review
        )
        return OrderReviewType(db_review)

    @strawberry.mutation
    async def create_company_review(self, info: strawberry.Info, input: CreateCompanyReviewInput) -> CompanyReviewType:
        """Create a new pending review for a company/tenant."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        # Enforce tenant check: users can only review their own tenant, or tenant context matches
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if tenant_id and tenant_id != input.tenant_id:
             raise ValidationError("You can only review companies within your tenant scope.")

        db = info.context.db
        db_review = await reviews_service.create_company_review(
            db=db,
            user_id=current_user.id,
            tenant_id=input.tenant_id,
            rating_points=input.rating_points,
            review_text=input.review
        )
        return CompanyReviewType(db_review)

    @strawberry.mutation
    async def update_product_review_status(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
        status: str
    ) -> ProductReviewType:
        """Approve or reject a product review (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_review = await reviews_service.update_product_review_status(
            db=db,
            review_id=id,
            status=status,
            moderator_id=current_user.id
        )
        return ProductReviewType(db_review)

    @strawberry.mutation
    async def update_order_review_status(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
        status: str
    ) -> OrderReviewType:
        """Approve or reject an order review (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_review = await reviews_service.update_order_review_status(
            db=db,
            review_id=id,
            status=status,
            moderator_id=current_user.id
        )
        return OrderReviewType(db_review)

    @strawberry.mutation
    async def update_company_review_status(
        self,
        info: strawberry.Info,
        id: uuid.UUID,
        status: str
    ) -> CompanyReviewType:
        """Approve or reject a company review (Requires Admin permissions)."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Authentication required.")
        if current_user.role not in ["TENANT_ADMIN", "SUPER_ADMIN"]:
            raise UnauthorizedError("You do not have permission to moderate reviews.")
        db = info.context.db
        db_review = await reviews_service.update_company_review_status(
            db=db,
            review_id=id,
            status=status,
            moderator_id=current_user.id
        )
        return CompanyReviewType(db_review)
