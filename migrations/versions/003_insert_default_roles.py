"""Insert default roles (user, admin)."""

from typing import Sequence, Union

from alembic import op

revision: str = "003_insert_default_roles"
down_revision: Union[str, None] = "002_system_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `roles.id` has no server_default in 001_initial migration,
    # so we generate UUIDs on insert via pgcrypto's gen_random_uuid().
    op.execute(
        """
        INSERT INTO roles (id, role)
        VALUES
            (gen_random_uuid(), 'user'),
            (gen_random_uuid(), 'admin')
        ON CONFLICT (role) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE role IN ('user', 'admin')")

