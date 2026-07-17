"""Add contact submissions, landing settings and roadmap tasks."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_contact_and_landing"
down_revision: Union[str, None] = "004_payment_robokassa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("consent_personal_data", sa.Boolean(), nullable=False),
        sa.Column("consent_privacy", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "landing_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "countdown_title",
            sa.String(),
            nullable=False,
            server_default="До релиза",
        ),
        sa.Column(
            "release_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("'2026-08-01'"),
        ),
        sa.CheckConstraint("id = 1", name="landing_settings_singleton"),
    )
    op.execute(
        """
        INSERT INTO landing_settings (id, countdown_title, release_date)
        VALUES (1, 'До релиза', '2026-08-01')
        """
    )

    op.create_table(
        "roadmap_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="roadmap_tasks_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("roadmap_tasks")
    op.drop_table("landing_settings")
    op.drop_table("contact_submissions")
