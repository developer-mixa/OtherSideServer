"""Add missing indexes on hot foreign-key lookups (payments.user_id, subscriptions.user_id)
and a partial index for unprocessed payment events — Postgres does not auto-index FK columns,
only the unique constraints/indexes we already had."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_performance_indexes"
down_revision: Union[str, None] = "008_user_consent_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_payment_events_unprocessed",
        "payment_events",
        ["payment_id"],
        postgresql_where=sa.text("processed IS FALSE"),
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_unprocessed", table_name="payment_events")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_payments_user_id", table_name="payments")
