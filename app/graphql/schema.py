import strawberry
from app.users.graphql import UserQuery, UserMutation
from app.tenants.graphql import TenantQuery, TenantMutation
from app.auth.graphql import AuthMutation
from app.products.products.graphql import ProductQuery, ProductMutation
from app.products.categories.graphql import CategoryQuery, CategoryMutation
from app.products.pricing.graphql import PricingQuery, PricingMutation
from app.media.graphql import MediaQuery, MediaMutation
from app.promotions.graphql import CouponQuery, CouponMutation
from app.deliveries.graphql import DeliveryQuery, DeliveryMutation
from app.orders.graphql import OrderQuery, OrderMutation
from app.reviews.graphql import ReviewQuery, ReviewMutation
from app.wallet.graphql import WalletQuery, WalletMutation
from app.referral.graphql import ReferralQuery, ReferralMutation
from app.payments.graphql import PaymentQuery, PaymentMutation
from app.subscriptions.graphql import SubscriptionQuery, SubscriptionMutation
from app.homepage.graphql import HomepageQuery, HomepageMutation
from app.dashboard.graphql import DashboardQuery

@strawberry.type
class Query(
    UserQuery,
    TenantQuery,
    ProductQuery,
    CategoryQuery,
    PricingQuery,
    MediaQuery,
    CouponQuery,
    DeliveryQuery,
    OrderQuery,
    ReviewQuery,
    WalletQuery,
    ReferralQuery,
    PaymentQuery,
    SubscriptionQuery,
    HomepageQuery,
    DashboardQuery
):
    pass

@strawberry.type
class Mutation(
    UserMutation,
    TenantMutation,
    AuthMutation,
    ProductMutation,
    CategoryMutation,
    PricingMutation,
    MediaMutation,
    CouponMutation,
    DeliveryMutation,
    OrderMutation,
    ReviewMutation,
    WalletMutation,
    ReferralMutation,
    PaymentMutation,
    SubscriptionMutation,
    HomepageMutation
):
    pass

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation
)
