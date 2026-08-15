import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.orders.models import Order
from app.users.models import User
from app.products.products.models import ProductStock, Product

class DashboardService:
    async def get_dashboard_data(
        self,
        db: AsyncSession,
        tenant_id: str,
        date_range: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        
        # Calculate date boundaries
        now = datetime.utcnow()
        if date_range == "TODAY":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif date_range == "LAST_5_DAYS":
            start_date = now - timedelta(days=5)
            end_date = now
        elif date_range == "LAST_7_DAYS":
            start_date = now - timedelta(days=7)
            end_date = now
        elif date_range == "LAST_MONTH":
            # Approximation for last 30 days
            start_date = now - timedelta(days=30)
            end_date = now
        elif date_range == "CUSTOM":
            if not start_date or not end_date:
                raise ValueError("start_date and end_date are required for CUSTOM date range")
        else:
            # Default to all time if not specified
            start_date = datetime.min
            end_date = now

        # Define common base queries
        order_base_query = select(Order).where(Order.tenant_id == tenant_id)
        if start_date and end_date:
            order_base_query = order_base_query.where(Order.created_at >= start_date, Order.created_at <= end_date)

        # 1. Total Revenue and Orders Count
        async def fetch_order_summary():
            stmt = select(
                func.sum(Order.grand_total).label("total_revenue"),
                func.count(Order.id).label("total_orders")
            ).select_from(order_base_query.subquery())
            res = await db.execute(stmt)
            row = res.one_or_none()
            return {
                "totalRevenue": float(row.total_revenue) if row and row.total_revenue else 0.0,
                "totalOrders": int(row.total_orders) if row and row.total_orders else 0
            }

        # 2. Active Customers Count
        async def fetch_active_customers():
            stmt = select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.role == "USER",
                User.status == "ACTIVE"
            )
            res = await db.execute(stmt)
            return int(res.scalar() or 0)

        # 3. Low Stock Items (threshold = 10)
        LOW_STOCK_THRESHOLD = 10
        async def fetch_low_stock_data():
            stmt = select(ProductStock, Product).join(
                Product, ProductStock.product_id == Product.id
            ).where(
                ProductStock.tenant_id == tenant_id,
                ProductStock.stock < LOW_STOCK_THRESHOLD
            )
            res = await db.execute(stmt)
            records = res.all()
            
            items = []
            for stock, product in records:
                items.append({
                    "id": str(stock.id),
                    "product_name": product.title,
                    "current_stock": stock.stock,
                    "minimum_stock": LOW_STOCK_THRESHOLD
                })
            return len(items), items

        # 4. Recent Orders (limit 10)
        async def fetch_recent_orders():
            stmt = select(Order, User).join(
                User, Order.user_id == User.id
            ).where(
                Order.tenant_id == tenant_id
            ).order_by(
                desc(Order.created_at)
            ).limit(10)
            
            res = await db.execute(stmt)
            records = res.all()
            
            recent_orders = []
            for order, user in records:
                recent_orders.append({
                    "id": str(order.id),
                    "order_number": str(order.id)[:8].upper(), # Derived from UUID
                    "customer_name": user.name,
                    "total_amount": float(order.grand_total),
                    "status": order.order_status,
                    "created_at": order.created_at
                })
            return recent_orders

        # 5. Revenue Trend (Group by Date)
        async def fetch_revenue_trend():
            # Ensure cross-database compatibility (Postgres)
            stmt = select(
                func.date_trunc('day', Order.created_at).label("day"),
                func.sum(Order.grand_total).label("revenue")
            ).where(
                Order.tenant_id == tenant_id
            )
            
            if start_date and end_date:
                stmt = stmt.where(Order.created_at >= start_date, Order.created_at <= end_date)
                
            stmt = stmt.group_by("day").order_by("day")
            
            res = await db.execute(stmt)
            records = res.all()
            
            trend = []
            for day, revenue in records:
                trend.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "revenue": float(revenue) if revenue else 0.0
                })
            return trend

        # Execute queries concurrently
        (
            order_summary,
            active_customers_count,
            low_stock_tuple,
            recent_orders,
            revenue_trend
        ) = await asyncio.gather(
            fetch_order_summary(),
            fetch_active_customers(),
            fetch_low_stock_data(),
            fetch_recent_orders(),
            fetch_revenue_trend()
        )
        
        low_stock_count, low_stock_items = low_stock_tuple

        return {
            "summary": {
                "total_revenue": order_summary["totalRevenue"],
                "total_orders": order_summary["totalOrders"],
                "active_customers": active_customers_count,
                "low_stock_items": low_stock_count
            },
            "revenue_trend": revenue_trend,
            "recent_orders": recent_orders,
            "low_stock_items": low_stock_items
        }

dashboard_service = DashboardService()
