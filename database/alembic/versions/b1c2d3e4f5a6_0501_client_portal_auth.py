"""0501_client_portal_auth

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-05-12 00:00:00.000000

Extends users.role CheckConstraint to include 'client_user'.
Adds users.client_id nullable UUID FK → clients.id ON DELETE SET NULL.
Adds index ix_users_client_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing role CheckConstraint (admin/consultor/comercial only)
    op.drop_constraint("users_role_check", "users", type_="check")

    # 2. Recreate with client_user included
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('admin', 'consultor', 'comercial', 'client_user')",
    )

    # 3. Add client_id nullable FK column
    op.add_column(
        "users",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 4. Add FK constraint
    op.create_foreign_key(
        "fk_users_client_id",
        "users",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 5. Add index for efficient client_id lookups
    op.create_index("ix_users_client_id", "users", ["client_id"], unique=False)


def downgrade() -> None:
    # Strict reverse of upgrade()

    # 5. Drop index
    op.drop_index("ix_users_client_id", table_name="users")

    # 4. Drop FK constraint
    op.drop_constraint("fk_users_client_id", "users", type_="foreignkey")

    # 3. Drop client_id column
    op.drop_column("users", "client_id")

    # 2. Drop the extended role CheckConstraint
    op.drop_constraint("users_role_check", "users", type_="check")

    # 1. Restore original role CheckConstraint (without client_user)
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('admin', 'consultor', 'comercial')",
    )
