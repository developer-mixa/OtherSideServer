"""Add users.consent_personal_data and consent_personal_data_at columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_user_consent_fields"
down_revision: Union[str, None] = "007_subscription_plan_duration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("consent_personal_data", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("consent_personal_data_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "consent_personal_data_at")
    op.drop_column("users", "consent_personal_data")
