"""0002_crm_core_domain

Revision ID: a1b2c3d4e5f6
Revises: 5216c59e63c5
Create Date: 2026-05-11 00:00:00.000000

Creates: clients, contacts, services, milestones, activity_log tables.
Adds: leads.converted_client_id (UUID FK → clients, ON DELETE SET NULL).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5216c59e63c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. clients
    op.create_table(
        "clients",
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
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "stage",
            sa.String(64),
            nullable=False,
            server_default="lead",
        ),
        sa.Column(
            "entered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("mrr_cents", sa.BigInteger(), nullable=True),
        sa.Column("lifetime_value_cents", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "stage IN ('lead','discovery_scheduled','discovery_done',"
            "'proposal_sent','active','lost')",
            name="ck_client_stage",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_stage", "clients", ["stage"], unique=False)
    op.create_index("ix_client_owner_id", "clients", ["owner_id"], unique=False)
    op.create_index("ix_client_name", "clients", ["name"], unique=False)

    # 2. contacts (FK → clients CASCADE)
    op.create_table(
        "contacts",
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
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contact_client_id", "contacts", ["client_id"], unique=False
    )

    # 3. services (FKs → clients CASCADE, users SET NULL)
    op.create_table(
        "services",
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
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "state",
            sa.String(64),
            nullable=False,
            server_default="scoping",
        ),
        sa.Column("progress_pct", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("setup_price_cents", sa.BigInteger(), nullable=True),
        sa.Column("monthly_cents", sa.BigInteger(), nullable=True),
        sa.Column("score_int", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "type IN ('assessment','development','formation')",
            name="ck_service_type",
        ),
        sa.CheckConstraint(
            "state IN ('scoping','running','review','completed','maintenance','paused')",
            name="ck_service_state",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_service_client_id", "services", ["client_id"], unique=False
    )
    op.create_index("ix_service_state", "services", ["state"], unique=False)

    # 4. milestones (FK → services CASCADE)
    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "n", name="uq_milestone_service_n"),
    )
    op.create_index(
        "ix_milestone_service_id", "milestones", ["service_id"], unique=False
    )

    # 5. activity_log (FKs → clients CASCADE, users SET NULL)
    op.create_table(
        "activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('stage_change','contact_added','contact_updated',"
            "'service_started','service_state_change','milestone_completed',"
            "'lead_converted','note')",
            name="ck_activity_log_kind",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Composite index: client_id + created_at DESC for the default listing query
    op.create_index(
        "ix_activity_log_client_id_created_at",
        "activity_log",
        ["client_id", sa.text("created_at DESC")],
        unique=False,
    )

    # 6. Add converted_client_id to leads
    op.add_column(
        "leads",
        sa.Column(
            "converted_client_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 7. FK on leads.converted_client_id → clients.id ON DELETE SET NULL
    op.create_foreign_key(
        "fk_lead_converted_client_id",
        "leads",
        "clients",
        ["converted_client_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Strict reverse of upgrade()

    # 7. Drop FK on leads.converted_client_id
    op.drop_constraint(
        "fk_lead_converted_client_id", "leads", type_="foreignkey"
    )

    # 6. Drop column from leads
    op.drop_column("leads", "converted_client_id")

    # 5. Drop activity_log
    op.drop_index(
        "ix_activity_log_client_id_created_at", table_name="activity_log"
    )
    op.drop_table("activity_log")

    # 4. Drop milestones
    op.drop_index("ix_milestone_service_id", table_name="milestones")
    op.drop_table("milestones")

    # 3. Drop services
    op.drop_index("ix_service_state", table_name="services")
    op.drop_index("ix_service_client_id", table_name="services")
    op.drop_table("services")

    # 2. Drop contacts
    op.drop_index("ix_contact_client_id", table_name="contacts")
    op.drop_table("contacts")

    # 1. Drop clients
    op.drop_index("ix_client_name", table_name="clients")
    op.drop_index("ix_client_owner_id", table_name="clients")
    op.drop_index("ix_client_stage", table_name="clients")
    op.drop_table("clients")
