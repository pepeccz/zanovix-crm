"""0506_lead_role_billing_profiles

Revision ID: a0b1c2d3e4f5
Revises: f5a6b7c8d9e0
Create Date: 2026-05-12 00:00:00.000000

Additive migration:
  1. Add leads.role (nullable String(100)).
  2. Create billing_profiles table with all columns, FK, constraints, index.

Downgrade is safe — drop index, drop table, drop column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Lead.role — nullable, additive
    op.add_column("leads", sa.Column("role", sa.String(length=100), nullable=True))

    # 2) billing_profiles table
    op.create_table(
        "billing_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(32), nullable=False),
        sa.Column("tax_id_type", sa.String(8), nullable=False),
        sa.Column("tax_regime", sa.String(32), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("province", sa.String(120), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column(
            "country",
            sa.String(2),
            nullable=False,
            server_default="ES",
        ),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "client_id",
            "tax_id",
            name="uq_billing_profile_client_tax_id",
        ),
        sa.CheckConstraint(
            "tax_id_type IN ('NIF','CIF','NIE','VAT')",
            name="ck_billing_profile_tax_id_type",
        ),
        sa.CheckConstraint(
            "tax_regime IN ('general','recargo_equivalencia','simplificado','exento','intracomunitario')",
            name="ck_billing_profile_tax_regime",
        ),
        sa.CheckConstraint(
            "char_length(country) = 2",
            name="ck_billing_profile_country_iso2",
        ),
    )
    op.create_index(
        "ix_billing_profile_client_id",
        "billing_profiles",
        ["client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_profile_client_id", table_name="billing_profiles")
    op.drop_table("billing_profiles")
    op.drop_column("leads", "role")
