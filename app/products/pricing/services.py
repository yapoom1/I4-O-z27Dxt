import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.products.products.services import product_service

from app.products.pricing.models import ProductPricingRule, ProductPrice, PricingType
from app.utils.audit import log_audit_event
from app.utils.exceptions import ValidationError

class PricingService:
    """Service handling dynamic price calculation, static prices, and pricing rules."""

    @staticmethod
    async def get_base_price(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        pricing_type: str = "selling_price"
    ) -> Optional[Decimal]:
        """Fetch the default base price mapped to the product for the given pricing type."""
        stmt = select(ProductPrice.price).join(
            PricingType, PricingType.id == ProductPrice.pricing_type_id
        ).where(
            (ProductPrice.product_id == product_id) &
            (PricingType.tenant_id == tenant_id) &
            (PricingType.type == pricing_type)
        )
        res = await db.execute(stmt)
        price_val = res.scalar_one_or_none()
        return Decimal(str(price_val)) if price_val is not None else None

    @staticmethod
    async def get_base_selling_price(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID
    ) -> Optional[Decimal]:
        """Fetch the default base selling price mapped to the product."""
        return await PricingService.get_base_price(db, tenant_id, product_id, "selling_price")

    @staticmethod
    async def resolve_pricing_type(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        requested_pricing_type: Optional[str] = None
    ) -> str:
        """
        Resolves the active pricing type name for a product.
        1. If a pricing type is explicitly requested, use that.
        2. If the product has a ProductAttributeValue linkage with a set pricing_type_id,
           resolve and return that pricing type's name.
        3. Fall back to the default "selling_price".
        """
        if requested_pricing_type:
            return requested_pricing_type.strip().lower()

        # Check ProductAttributeValue linkages
        from app.products.products.models import ProductAttributeValue
        stmt = select(PricingType.type).join(
            ProductAttributeValue, ProductAttributeValue.pricing_type_id == PricingType.id
        ).where(
            (ProductAttributeValue.product_id == product_id) &
            (PricingType.tenant_id == tenant_id)
        )
        res = await db.execute(stmt)
        override_type = res.scalar_one_or_none()
        if override_type:
            return override_type

        return "selling_price"

    @staticmethod
    async def get_effective_price(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        location_id: Optional[uuid.UUID] = None,
        pincode: Optional[str] = None,
        current_time: Optional[datetime] = None,
        current_stock: Optional[int] = None,
        pricing_type: Optional[str] = None
    ) -> Decimal:
        """
        Calculates the final dynamic price based on rules and customer context parameters.
        """
        resolved_type_name = await PricingService.resolve_pricing_type(db, tenant_id, product_id, pricing_type)
        base_price = await PricingService.get_base_price(db, tenant_id, product_id, resolved_type_name)
        if base_price is None:
            raise ValidationError(f"Product price for pricing type '{resolved_type_name}' not configured.")

        current_time = current_time or datetime.utcnow()
        current_hour = current_time.hour
        current_day = current_time.weekday()  # Monday is 0, Sunday is 6

        # Fetch rules matching this pricing type
        if resolved_type_name == "selling_price":
            stmt = select(ProductPricingRule).outerjoin(
                PricingType, PricingType.id == ProductPricingRule.pricing_type_id
            ).where(
                (ProductPricingRule.tenant_id == tenant_id) &
                (ProductPricingRule.product_id == product_id) &
                ((PricingType.type == "selling_price") | (ProductPricingRule.pricing_type_id.is_(None)))
            ).order_by(ProductPricingRule.priority.desc())
        else:
            stmt = select(ProductPricingRule).join(
                PricingType, PricingType.id == ProductPricingRule.pricing_type_id
            ).where(
                (ProductPricingRule.tenant_id == tenant_id) &
                (ProductPricingRule.product_id == product_id) &
                (PricingType.type == resolved_type_name)
            ).order_by(ProductPricingRule.priority.desc())
        
        res = await db.execute(stmt)
        rules = res.scalars().all()

        matching_rule: Optional[ProductPricingRule] = None

        for rule in rules:
            # 1. Quantity constraints
            if rule.min_quantity is not None and quantity < rule.min_quantity:
                continue
            if rule.max_quantity is not None and quantity > rule.max_quantity:
                continue

            # 2. Location constraints
            if rule.location_id is not None and rule.location_id != location_id:
                continue
            if rule.pincode is not None:
                cleaned_rule_pin = rule.pincode.strip().lower()
                cleaned_input_pin = (pincode or "").strip().lower()
                if cleaned_rule_pin != cleaned_input_pin:
                    continue

            # 3. Absolute Date/Time constraints
            if rule.start_time is not None and current_time < rule.start_time:
                continue
            if rule.end_time is not None and current_time > rule.end_time:
                continue

            # 4. Recurring Time constraints
            if rule.day_of_week is not None and current_day != rule.day_of_week:
                continue
            
            if rule.start_hour is not None and rule.end_hour is not None:
                if rule.start_hour <= rule.end_hour:
                    if not (rule.start_hour <= current_hour < rule.end_hour):
                        continue
                else:  # Overnight intervals (e.g. 22:00 to 02:00)
                    if not (current_hour >= rule.start_hour or current_hour < rule.end_hour):
                        continue
            elif rule.start_hour is not None:
                if current_hour < rule.start_hour:
                    continue
            elif rule.end_hour is not None:
                if current_hour >= rule.end_hour:
                    continue

            # 5. Stock Level constraints
            if current_stock is not None:
                if rule.min_stock is not None and current_stock < rule.min_stock:
                    continue
                if rule.max_stock is not None and current_stock > rule.max_stock:
                    continue
            elif rule.min_stock is not None or rule.max_stock is not None:
                # If stock context is missing, rules depending on stock level are skipped
                continue

            # If all conditions pass, we select the highest priority rule (already ordered descending)
            matching_rule = rule
            break

        if not matching_rule:
            return base_price

        # Apply winning pricing rule adjustment
        effective_price = base_price
        val = Decimal(str(matching_rule.value))

        if matching_rule.rule_type == "OVERRIDE":
            effective_price = val
        elif matching_rule.rule_type == "DISCOUNT_PERCENT":
            discount = (effective_price * val) / Decimal("100")
            effective_price -= discount
        elif matching_rule.rule_type == "DISCOUNT_FIXED":
            effective_price -= val
        elif matching_rule.rule_type == "MARKUP_PERCENT":
            markup = (effective_price * val) / Decimal("100")
            effective_price += markup
        elif matching_rule.rule_type == "MARKUP_FIXED":
            effective_price += val

        return max(Decimal("0.00"), effective_price.quantize(Decimal("0.01")))

    @staticmethod
    async def batch_get_effective_prices(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        keys: List[tuple]
    ) -> List[Decimal]:
        """
        Batch calculate effective prices.
        Each tuple is: (product_id, quantity, location_id, pincode, requested_pricing_type, current_stock)
        """
        from app.products.products.models import ProductAttributeValue
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        current_day = current_time.weekday()

        product_ids = list(set([k[0] for k in keys]))
        if not product_ids:
            return []

        # 1. Batch resolve pricing types
        stmt_pt = select(ProductAttributeValue.product_id, PricingType.type).join(
            PricingType, ProductAttributeValue.pricing_type_id == PricingType.id
        ).where(
            (ProductAttributeValue.product_id.in_(product_ids)) &
            (PricingType.tenant_id == tenant_id)
        )
        res_pt = await db.execute(stmt_pt)
        resolved_types = {row.product_id: row.type for row in res_pt.all()}

        # 2. Batch fetch base prices for all pricing types
        stmt_bp = select(ProductPrice.product_id, PricingType.type, ProductPrice.price).join(
            PricingType, PricingType.id == ProductPrice.pricing_type_id
        ).where(
            (ProductPrice.product_id.in_(product_ids)) &
            (PricingType.tenant_id == tenant_id)
        )
        res_bp = await db.execute(stmt_bp)
        base_prices = {}
        for row in res_bp.all():
            base_prices[(row.product_id, row.type)] = Decimal(str(row.price))

        # 3. Batch fetch all rules
        stmt_rules = select(ProductPricingRule, PricingType.type).outerjoin(
            PricingType, PricingType.id == ProductPricingRule.pricing_type_id
        ).where(
            (ProductPricingRule.tenant_id == tenant_id) &
            (ProductPricingRule.product_id.in_(product_ids))
        ).order_by(ProductPricingRule.priority.desc())
        res_rules = await db.execute(stmt_rules)
        
        from collections import defaultdict
        rules_by_product = defaultdict(list)
        for rule, pt_type in res_rules.all():
            rules_by_product[rule.product_id].append((rule, pt_type))

        results = []
        for key in keys:
            product_id, quantity, location_id, pincode, requested_type, current_stock = key
            
            # Resolve type
            if requested_type:
                resolved_type_name = requested_type.strip().lower()
            else:
                resolved_type_name = resolved_types.get(product_id, "selling_price")

            # Get base price
            base_price = base_prices.get((product_id, resolved_type_name))
            if base_price is None:
                results.append(Decimal("0.00"))
                continue

            matching_rule = None
            for rule, pt_type in rules_by_product.get(product_id, []):
                # Check if rule matches pricing type
                if pt_type is not None and pt_type != resolved_type_name:
                    if resolved_type_name != "selling_price":
                        continue
                    elif pt_type != "selling_price":
                        continue

                # 1. Quantity constraints
                if rule.min_quantity is not None and quantity < rule.min_quantity:
                    continue
                if rule.max_quantity is not None and quantity > rule.max_quantity:
                    continue

                # 2. Location constraints
                if rule.location_id is not None and rule.location_id != location_id:
                    continue
                if rule.pincode is not None:
                    cleaned_rule_pin = rule.pincode.strip().lower()
                    cleaned_input_pin = (pincode or "").strip().lower()
                    if cleaned_rule_pin != cleaned_input_pin:
                        continue

                # 3. Absolute Date/Time constraints
                if rule.start_time is not None and current_time < rule.start_time:
                    continue
                if rule.end_time is not None and current_time > rule.end_time:
                    continue

                # 4. Recurring Time constraints
                if rule.day_of_week is not None and current_day != rule.day_of_week:
                    continue
                
                if rule.start_hour is not None and rule.end_hour is not None:
                    if rule.start_hour <= rule.end_hour:
                        if not (rule.start_hour <= current_hour < rule.end_hour):
                            continue
                    else:  # Overnight intervals
                        if not (current_hour >= rule.start_hour or current_hour < rule.end_hour):
                            continue
                elif rule.start_hour is not None:
                    if current_hour < rule.start_hour:
                        continue
                elif rule.end_hour is not None:
                    if current_hour >= rule.end_hour:
                        continue

                # 5. Stock Level constraints
                if current_stock is not None:
                    if rule.min_stock is not None and current_stock < rule.min_stock:
                        continue
                    if rule.max_stock is not None and current_stock > rule.max_stock:
                        continue
                elif rule.min_stock is not None or rule.max_stock is not None:
                    continue

                matching_rule = rule
                break

            if not matching_rule:
                results.append(base_price)
                continue

            effective_price = base_price
            val = Decimal(str(matching_rule.value))
            if matching_rule.rule_type == "OVERRIDE":
                effective_price = val
            elif matching_rule.rule_type == "DISCOUNT_PERCENT":
                effective_price -= (effective_price * val) / Decimal("100")
            elif matching_rule.rule_type == "DISCOUNT_FIXED":
                effective_price -= val
            elif matching_rule.rule_type == "MARKUP_PERCENT":
                effective_price += (effective_price * val) / Decimal("100")
            elif matching_rule.rule_type == "MARKUP_FIXED":
                effective_price += val

            results.append(max(Decimal("0.00"), effective_price.quantize(Decimal("0.01"))))

        return results

    @staticmethod
    async def create_pricing_rule(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        name: str,
        priority: int,
        rule_type: str,
        value: float,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        location_id: Optional[uuid.UUID] = None,
        pincode: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        day_of_week: Optional[int] = None,
        start_hour: Optional[int] = None,
        end_hour: Optional[int] = None,
        min_stock: Optional[int] = None,
        max_stock: Optional[int] = None,
        pricing_type_id: Optional[uuid.UUID] = None
    ) -> ProductPricingRule:
        """Create a new dynamic pricing rule for a product."""
        rule_type = rule_type.upper().strip()
        valid_types = ["OVERRIDE", "DISCOUNT_PERCENT", "DISCOUNT_FIXED", "MARKUP_PERCENT", "MARKUP_FIXED"]
        if rule_type not in valid_types:
            raise ValidationError(f"Invalid rule type. Must be one of {valid_types}.")

        if value < 0:
            raise ValidationError("Pricing adjustment value must be non-negative.")

        if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
            raise ValidationError("day_of_week must be between 0 (Monday) and 6 (Sunday).")

        if start_hour is not None and (start_hour < 0 or start_hour > 23):
            raise ValidationError("start_hour must be between 0 and 23.")

        if end_hour is not None and (end_hour < 0 or end_hour > 23):
            raise ValidationError("end_hour must be between 0 and 23.")

        # Verify product exists in tenant
        product = await product_service.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        if pricing_type_id is not None:
            # Verify pricing type exists in tenant
            pricing_type = await PricingService.get_pricing_type_by_id(db, tenant_id, pricing_type_id)
            if not pricing_type:
                raise ValidationError("Pricing type not found or belongs to another tenant.")

        rule = ProductPricingRule(
            tenant_id=tenant_id,
            product_id=product_id,
            name=name,
            priority=priority,
            rule_type=rule_type,
            value=value,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            location_id=location_id,
            pincode=pincode,
            start_time=start_time,
            end_time=end_time,
            day_of_week=day_of_week,
            start_hour=start_hour,
            end_hour=end_hour,
            min_stock=min_stock,
            max_stock=max_stock,
            pricing_type_id=pricing_type_id
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete_pricing_rule(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID
    ) -> bool:
        """Delete a dynamic pricing rule."""
        stmt = select(ProductPricingRule).where(
            (ProductPricingRule.id == rule_id) &
            (ProductPricingRule.tenant_id == tenant_id)
        )
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            raise ValidationError("Pricing rule not found.")

        await db.delete(rule)
        await db.commit()
        return True

    # --- Pricing Type Management ---

    @staticmethod
    async def get_pricing_types(db: AsyncSession, tenant_id: uuid.UUID) -> List[PricingType]:
        """Fetch all pricing types configured under a tenant."""
        stmt = select(PricingType).where(PricingType.tenant_id == tenant_id).order_by(PricingType.type.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_pricing_type_by_id(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        pricing_type_id: uuid.UUID
    ) -> Optional[PricingType]:
        """Fetch a single pricing type by ID scoped to a tenant."""
        stmt = select(PricingType).where(
            (PricingType.id == pricing_type_id) &
            (PricingType.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_pricing_type(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        type_name: str,
        user_id: Optional[uuid.UUID] = None
    ) -> PricingType:
        """Create a new pricing type (e.g., selling_price, cost) under a tenant."""
        type_name = type_name.strip().lower()
        if not type_name:
            raise ValidationError("Pricing type name cannot be empty.")

        stmt = select(PricingType).where(
            (PricingType.tenant_id == tenant_id) &
            (PricingType.type == type_name)
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ValidationError(f"Pricing type '{type_name}' already exists under this tenant.")

        pricing_type = PricingType(
            tenant_id=tenant_id,
            type=type_name
        )
        db.add(pricing_type)
        await db.commit()
        await db.refresh(pricing_type)

        await log_audit_event(
            action="PRICING_TYPE_CREATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "pricing_type_id": str(pricing_type.id),
                "type": type_name
            }
        )

        return pricing_type

    @staticmethod
    async def update_pricing_type(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        pricing_type_id: uuid.UUID,
        type_name: str,
        user_id: Optional[uuid.UUID] = None
    ) -> PricingType:
        """Update an existing pricing type's name."""
        pricing_type = await PricingService.get_pricing_type_by_id(db, tenant_id, pricing_type_id)
        if not pricing_type:
            raise ValidationError("Pricing type not found or belongs to another tenant.")

        type_name = type_name.strip().lower()
        if not type_name:
            raise ValidationError("Pricing type name cannot be empty.")

        if type_name != pricing_type.type:
            stmt = select(PricingType).where(
                (PricingType.tenant_id == tenant_id) &
                (PricingType.type == type_name) &
                (PricingType.id != pricing_type_id)
            )
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                raise ValidationError(f"Pricing type '{type_name}' already exists under this tenant.")

        pricing_type.type = type_name
        await db.commit()
        await db.refresh(pricing_type)

        await log_audit_event(
            action="PRICING_TYPE_UPDATED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "pricing_type_id": str(pricing_type_id),
                "type": type_name
            }
        )

        return pricing_type

    @staticmethod
    async def delete_pricing_type(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        pricing_type_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a pricing type scoped to a tenant."""
        pricing_type = await PricingService.get_pricing_type_by_id(db, tenant_id, pricing_type_id)
        if not pricing_type:
            raise ValidationError("Pricing type not found or belongs to another tenant.")

        await db.delete(pricing_type)
        await db.commit()

        await log_audit_event(
            action="PRICING_TYPE_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={"pricing_type_id": str(pricing_type_id)}
        )

        return True

    # --- Product Price Management ---

    @staticmethod
    async def get_product_prices(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> List[ProductPrice]:
        """Fetch all prices assigned to a specific product scoped to a tenant."""
        product = await product_service.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        stmt = select(ProductPrice).where(ProductPrice.product_id == product_id).order_by(ProductPrice.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def set_product_price(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        pricing_type_id: uuid.UUID,
        price_value: float,
        user_id: Optional[uuid.UUID] = None
    ) -> ProductPrice:
        """Set or update a specific price mapping for a product."""
        product = await product_service.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        pricing_type = await PricingService.get_pricing_type_by_id(db, tenant_id, pricing_type_id)
        if not pricing_type:
            raise ValidationError("Pricing type not found or belongs to another tenant.")

        if price_value < 0:
            raise ValidationError("Price value cannot be negative.")

        stmt = select(ProductPrice).where(
            (ProductPrice.product_id == product_id) &
            (ProductPrice.pricing_type_id == pricing_type_id)
        )
        res = await db.execute(stmt)
        prod_price = res.scalar_one_or_none()

        if prod_price:
            prod_price.price = price_value
        else:
            prod_price = ProductPrice(
                product_id=product_id,
                pricing_type_id=pricing_type_id,
                price=price_value
            )
            db.add(prod_price)

        await db.commit()
        await db.refresh(prod_price)

        await log_audit_event(
            action="PRODUCT_PRICE_SET",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "product_id": str(product_id),
                "pricing_type_id": str(pricing_type_id),
                "price": str(price_value)
            }
        )

        return prod_price

    @staticmethod
    async def delete_product_price(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        pricing_type_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Delete a price mapping scoped to a tenant."""
        product = await product_service.get_product_by_id(tenant_id, product_id)
        if not product:
            raise ValidationError("Product not found or belongs to another tenant.")

        pricing_type = await PricingService.get_pricing_type_by_id(db, tenant_id, pricing_type_id)
        if not pricing_type:
            raise ValidationError("Pricing type not found or belongs to another tenant.")

        stmt = select(ProductPrice).where(
            (ProductPrice.product_id == product_id) &
            (ProductPrice.pricing_type_id == pricing_type_id)
        )
        res = await db.execute(stmt)
        prod_price = res.scalar_one_or_none()

        if not prod_price:
            raise ValidationError("Product price mapping not found.")

        await db.delete(prod_price)
        await db.commit()

        await log_audit_event(
            action="PRODUCT_PRICE_DELETED",
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            details={
                "product_id": str(product_id),
                "pricing_type_id": str(pricing_type_id)
            }
        )

        return True

pricing_service = PricingService()
