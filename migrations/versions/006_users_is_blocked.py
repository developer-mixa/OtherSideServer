"""Add users.is_blocked column."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_users_is_blocked"
down_revision: Union[str, None] = "005_contact_and_landing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_blocked")
