import strawberry
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.dashboard.services import dashboard_service

@strawberry.enum
class DashboardDateRange(Enum):
    TODAY = "TODAY"
    LAST_5_DAYS = "LAST_5_DAYS"
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_MONTH = "LAST_MONTH"
    CUSTOM = "CUSTOM"

@strawberry.type
class DashboardSummary:
    total_revenue: float = strawberry.field(name="totalRevenue")
    total_orders: int = strawberry.field(name="totalOrders")
    active_customers: int = strawberry.field(name="activeCustomers")
    low_stock_items: int = strawberry.field(name="lowStockItems")

@strawberry.type
class RevenueData:
    date: str
    revenue: float

@strawberry.type
class DashboardOrder:
    id: str
    order_number: str = strawberry.field(name="orderNumber")
    customer_name: str = strawberry.field(name="customerName")
    total_amount: float = strawberry.field(name="totalAmount")
    status: str
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class LowStockItem:
    id: str
    product_name: str = strawberry.field(name="productName")
    current_stock: int = strawberry.field(name="currentStock")
    minimum_stock: int = strawberry.field(name="minimumStock")

@strawberry.type
class DashboardResponse:
    summary: DashboardSummary
    revenue_trend: List[RevenueData] = strawberry.field(name="revenueTrend")
    recent_orders: List[DashboardOrder] = strawberry.field(name="recentOrders")
    low_stock_items: List[LowStockItem] = strawberry.field(name="lowStockItems")

@strawberry.type
class DashboardQuery:
    @strawberry.field
    async def dashboard(
        self, 
        info: strawberry.Info,
        date_range: DashboardDateRange = DashboardDateRange.LAST_7_DAYS,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> DashboardResponse:
        
        user = info.context.user
        if not user:
            from app.utils.exceptions import UnauthorizedError
            raise UnauthorizedError("Authentication required.")
        
        target_tenant_id = None
        
        if user.role == "SUPER_ADMIN":
            # Super admin can specify a tenantId or view the platform dashboard (None)
            target_tenant_id = tenant_id
        else:
            # For TENANT_ADMIN and USER, use their tenant_id
            target_tenant_id = str(user.tenant_id) if user.tenant_id else info.context.tenant_id
            
            if not target_tenant_id:
                from app.utils.exceptions import UnauthorizedError
                raise UnauthorizedError("Tenant context missing.")
            
            # If they try to query another tenant's dashboard, deny
            if tenant_id and str(tenant_id) != str(target_tenant_id):
                from app.utils.exceptions import UnauthorizedError
                raise UnauthorizedError("You do not have permission to view this tenant's dashboard.")

        data = await dashboard_service.get_dashboard_data(
            db=info.context.db,
            tenant_id=target_tenant_id,
            date_range=date_range.value,
            start_date=start_date,
            end_date=end_date
        )
        
        summary = DashboardSummary(**data["summary"])
        revenue_trend = [RevenueData(**t) for t in data["revenue_trend"]]
        recent_orders = [DashboardOrder(**o) for o in data["recent_orders"]]
        low_stock_items = [LowStockItem(**i) for i in data["low_stock_items"]]
        
        return DashboardResponse(
            summary=summary,
            revenue_trend=revenue_trend,
            recent_orders=recent_orders,
            low_stock_items=low_stock_items
        )
