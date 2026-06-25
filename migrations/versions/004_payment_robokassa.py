"""Add plan pricing, payment fulfillment fields, and Robokassa constraints."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_payment_robokassa"
down_revision: Union[str, None] = "003_insert_default_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column(
            "price_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "source_payment_id",
            sa.UUID(),
            sa.ForeignKey("payments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "payments_status_check",
        "payments",
        "status IN ('pending', 'paid', 'failed', 'cancelled')",
    )

    op.create_index(
        "uq_subscriptions_permanent_user_plan",
        "subscriptions",
        ["user_id", "plan_id"],
        unique=True,
        postgresql_where=sa.text("active_until IS NULL AND plan_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_subscriptions_permanent_user_plan", table_name="subscriptions")
    op.drop_constraint("payments_status_check", "payments", type_="check")
    op.drop_column("subscriptions", "source_payment_id")
    op.drop_column("subscription_plans", "is_active")
    op.drop_column("subscription_plans", "price_amount")
