"""Add system_settings table for maintenance mode."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_system_settings"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "maintenance_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint("id = 1", name="system_settings_singleton"),
    )
    op.execute(
        "INSERT INTO system_settings (id, maintenance_mode) VALUES (1, false)"
    )


def downgrade() -> None:
    op.drop_table("system_settings")
