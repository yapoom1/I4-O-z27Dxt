import uuid
from typing import List, Optional
import strawberry

from datetime import datetime
from app.deliveries.services import delivery_service, delivery_rule_service, delivery_agent_service
from app.users.graphql import UserCartType
from app.utils.exceptions import UnauthorizedError, ValidationError

@strawberry.type
class DeliveryOptionType:
    service_name: str = strawberry.field(name="serviceName")
    delivery_fee: float = strawberry.field(name="deliveryFee")
    estimated_days: int = strawberry.field(name="estimatedDays")

    def __init__(self, service_name: str, delivery_fee: float, estimated_days: int):
        self.service_name = service_name
        self.delivery_fee = delivery_fee
        self.estimated_days = estimated_days

@strawberry.type
class DeliveryRuleType:
    id: uuid.UUID
    field: str
    operator: str
    value: str
    carrier: str
    created_at: datetime
    updated_at: datetime

    def __init__(self, db_rule):
        self.id = db_rule.id
        self.field = db_rule.field
        self.operator = db_rule.operator
        self.value = db_rule.value
        self.carrier = db_rule.carrier
        self.created_at = db_rule.created_at
        self.updated_at = db_rule.updated_at

@strawberry.type
class DeliveryAgentType:
    id: uuid.UUID
    name: str
    zone: str
    active_orders: int
    status: str
    created_at: datetime
    updated_at: datetime

    def __init__(self, db_agent):
        self.id = db_agent.id
        self.name = db_agent.name
        self.zone = db_agent.zone
        self.active_orders = db_agent.active_orders
        self.status = db_agent.status
        self.created_at = db_agent.created_at
        self.updated_at = db_agent.updated_at

@strawberry.input
class DeliveryRuleInput:
    field: str
    operator: str
    value: str
    carrier: str

@strawberry.input
class UpdateDeliveryRuleInput:
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[str] = None
    carrier: Optional[str] = None

@strawberry.type
class DeliveryQuery:
    @strawberry.field
    async def delivery_quotes(self, info: strawberry.Info, address_id: uuid.UUID) -> List[DeliveryOptionType]:
        """Fetch available shipping quotes for the provided address."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        # Check if address exists and belongs to user first
        from app.users.services import user_service
        addr = await user_service.get_user_address_by_id(db, current_user.id, address_id)
        if not addr:
            raise ValidationError("Address not found or does not belong to the user.")

        quotes = await delivery_service.get_delivery_quotes(db, tenant_id, address_id)
        return [
            DeliveryOptionType(
                service_name=q["service_name"],
                delivery_fee=float(q["delivery_fee"]),
                estimated_days=q["estimated_days"]
            )
            for q in quotes
        ]

    @strawberry.field
    async def delivery_rules(self, info: strawberry.Info) -> List[DeliveryRuleType]:
        """Fetch all delivery rules for the tenant."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        rules = await delivery_rule_service.get_delivery_rules(db, tenant_id)
        return [DeliveryRuleType(r) for r in rules]

    @strawberry.field
    async def delivery_agents(self, info: strawberry.Info) -> List[DeliveryAgentType]:
        """Fetch all delivery agents for the tenant."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        agents = await delivery_agent_service.get_delivery_agents(db, tenant_id)
        return [DeliveryAgentType(a) for a in agents]

@strawberry.type
class DeliveryMutation:
    @strawberry.mutation
    async def select_delivery_option(
        self,
        info: strawberry.Info,
        address_id: uuid.UUID,
        service_name: str
    ) -> UserCartType:
        """Select a delivery quote and link it to the user's cart."""
        current_user = info.context.user
        if not current_user:
            raise UnauthorizedError("Not authenticated.")
        
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")

        cart = await delivery_service.apply_delivery_to_cart(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            address_id=address_id,
            service_name=service_name
        )
        return UserCartType(cart)

    @strawberry.mutation
    async def create_delivery_rule(self, info: strawberry.Info, input: DeliveryRuleInput) -> DeliveryRuleType:
        """Create a new delivery rule."""
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        rule = await delivery_rule_service.create_delivery_rule(
            db, tenant_id, input.field, input.operator, input.value, input.carrier
        )
        return DeliveryRuleType(rule)

    @strawberry.mutation
    async def update_delivery_rule(self, info: strawberry.Info, rule_id: uuid.UUID, input: UpdateDeliveryRuleInput) -> DeliveryRuleType:
        """Update an existing delivery rule."""
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        kwargs = {k: v for k, v in input.__dict__.items() if v is not None}
        rule = await delivery_rule_service.update_delivery_rule(db, tenant_id, rule_id, **kwargs)
        return DeliveryRuleType(rule)

    @strawberry.mutation
    async def delete_delivery_rule(self, info: strawberry.Info, rule_id: uuid.UUID) -> bool:
        """Delete a delivery rule."""
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        return await delivery_rule_service.delete_delivery_rule(db, tenant_id, rule_id)

    @strawberry.mutation
    async def create_delivery_agent(self, info: strawberry.Info, name: str, zone: str) -> DeliveryAgentType:
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        agent = await delivery_agent_service.create_delivery_agent(db, tenant_id, name, zone)
        return DeliveryAgentType(agent)

    @strawberry.mutation
    async def update_delivery_agent_status(self, info: strawberry.Info, agent_id: uuid.UUID, status: str) -> DeliveryAgentType:
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        agent = await delivery_agent_service.update_delivery_agent_status(db, tenant_id, agent_id, status)
        return DeliveryAgentType(agent)

    @strawberry.mutation
    async def delete_delivery_agent(self, info: strawberry.Info, agent_id: uuid.UUID) -> bool:
        current_user = info.context.user
        if not current_user or current_user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise UnauthorizedError("Not authenticated or not authorized.")
        db = info.context.db
        tenant_id = info.context.tenant_id or current_user.tenant_id
        if not tenant_id:
            raise ValidationError("Tenant ID context is missing.")
        
        return await delivery_agent_service.delete_delivery_agent(db, tenant_id, agent_id)
