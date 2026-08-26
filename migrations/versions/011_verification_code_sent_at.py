"""Track when a verification code was last emailed, to throttle resends."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_verification_code_sent_at"
down_revision: Union[str, None] = "010_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("verification_code_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Left NULL on purpose: backfilling from the expiry would put the timestamp in the
    # future and lock anyone mid-signup out of resending. NULL means "no code sent yet",
    # so their first resend after the deploy goes through and the cooldown starts there.


def downgrade() -> None:
    op.drop_column("users", "verification_code_sent_at")
