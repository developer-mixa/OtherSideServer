"""Add email verification code columns to users."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_email_verification"
down_revision: Union[str, None] = "009_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verification_code_hash", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("verification_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "verification_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    # Accounts created before this feature existed never went through the code flow —
    # grandfather them in so they aren't locked out of login by the new is_verified gate.
    op.execute("UPDATE users SET is_verified = true WHERE is_verified = false")


def downgrade() -> None:
    op.drop_column("users", "verification_attempts")
    op.drop_column("users", "verification_code_expires_at")
    op.drop_column("users", "verification_code_hash")
