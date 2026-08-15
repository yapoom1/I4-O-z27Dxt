"""add subscription module

Revision ID: f1a2b3c4d5e6
Revises: 5b5acce85f20
Create Date: 2026-06-08 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '5b5acce85f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create subscription tables."""
    # 1. subscription_plans (no external FK dependencies)
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('billing_cycle', sa.String(20), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('title'),
    )

    # 2. subscription_features (FK -> subscription_plans)
    op.create_table(
        'subscription_features',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('user_limit', sa.Integer(), nullable=True),
        sa.Column('product_limit', sa.Integer(), nullable=True),
        sa.Column('coupon_limit', sa.Integer(), nullable=True),
        sa.Column('cod_enabled', sa.Boolean(), nullable=False),
        sa.Column('cms_enabled', sa.Boolean(), nullable=False),
        sa.Column('otp_login_enabled', sa.Boolean(), nullable=False),
        sa.Column('custom_domain_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id'),
    )
    op.create_index(
        op.f('ix_subscription_features_plan_id'),
        'subscription_features', ['plan_id'], unique=True
    )

    # 3. tenant_subscriptions (FK -> tenants, subscription_plans, coupons)
    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('plan_title_snapshot', sa.String(100), nullable=False),
        sa.Column('plan_price_snapshot', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('coupon_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tenant_subscriptions_tenant_id'),
        'tenant_subscriptions', ['tenant_id'], unique=False
    )
    op.create_index(
        op.f('ix_tenant_subscriptions_plan_id'),
        'tenant_subscriptions', ['plan_id'], unique=False
    )
    op.create_index(
        op.f('ix_tenant_subscriptions_status'),
        'tenant_subscriptions', ['status'], unique=False
    )
    op.create_index(
        op.f('ix_tenant_subscriptions_coupon_id'),
        'tenant_subscriptions', ['coupon_id'], unique=False
    )

    # 4. tenant_subscription_payments (FK -> tenant_subscriptions)
    op.create_table(
        'tenant_subscription_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_subscription_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('transaction_id', sa.String(255), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['tenant_subscription_id'], ['tenant_subscriptions.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index(
        op.f('ix_tenant_subscription_payments_tenant_subscription_id'),
        'tenant_subscription_payments', ['tenant_subscription_id'], unique=False
    )
    op.create_index(
        op.f('ix_tenant_subscription_payments_status'),
        'tenant_subscription_payments', ['status'], unique=False
    )
    op.create_index(
        op.f('ix_tenant_subscription_payments_transaction_id'),
        'tenant_subscription_payments', ['transaction_id'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema — drop subscription tables in reverse dependency order."""
    op.drop_index(
        op.f('ix_tenant_subscription_payments_transaction_id'),
        table_name='tenant_subscription_payments'
    )
    op.drop_index(
        op.f('ix_tenant_subscription_payments_status'),
        table_name='tenant_subscription_payments'
    )
    op.drop_index(
        op.f('ix_tenant_subscription_payments_tenant_subscription_id'),
        table_name='tenant_subscription_payments'
    )
    op.drop_table('tenant_subscription_payments')

    op.drop_index(
        op.f('ix_tenant_subscriptions_coupon_id'), table_name='tenant_subscriptions'
    )
    op.drop_index(
        op.f('ix_tenant_subscriptions_status'), table_name='tenant_subscriptions'
    )
    op.drop_index(
        op.f('ix_tenant_subscriptions_plan_id'), table_name='tenant_subscriptions'
    )
    op.drop_index(
        op.f('ix_tenant_subscriptions_tenant_id'), table_name='tenant_subscriptions'
    )
    op.drop_table('tenant_subscriptions')

    op.drop_index(
        op.f('ix_subscription_features_plan_id'), table_name='subscription_features'
    )
    op.drop_table('subscription_features')

    op.drop_table('subscription_plans')
