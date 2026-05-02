"""0001_initial

Revision ID: 5216c59e63c5
Revises:
Create Date: 2026-05-02 14:22:55.395497

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5216c59e63c5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users table ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'consultor', 'comercial')",
            name="users_role_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- leads table ---
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(200), nullable=True),
        sa.Column("vertical", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="'{}'::jsonb",
        ),
        sa.CheckConstraint(
            "vertical IN ('clinicas_dentales','general')",
            name="ck_lead_vertical",
        ),
        sa.CheckConstraint(
            "channel IN ('email_marketing','cold_calling','networking',"
            "'referral','web_form','other')",
            name="ck_lead_channel",
        ),
        sa.CheckConstraint(
            "status IN ('new','contacted','qualified','disqualified','converted')",
            name="ck_lead_status",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Non-unique index on email (decision #1 — duplicates allowed in MVP)
    op.create_index("ix_lead_email", "leads", ["email"], unique=False)
    op.create_index("ix_lead_status", "leads", ["status"], unique=False)
    op.create_index("ix_lead_vertical", "leads", ["vertical"], unique=False)
    op.create_index("ix_lead_owner_id", "leads", ["owner_id"], unique=False)
    # Descending index for the default listing sort (created_at DESC)
    op.create_index(
        "ix_lead_created_at_desc",
        "leads",
        [sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lead_created_at_desc", table_name="leads")
    op.drop_index("ix_lead_owner_id", table_name="leads")
    op.drop_index("ix_lead_vertical", table_name="leads")
    op.drop_index("ix_lead_status", table_name="leads")
    op.drop_index("ix_lead_email", table_name="leads")
    op.drop_table("leads")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
