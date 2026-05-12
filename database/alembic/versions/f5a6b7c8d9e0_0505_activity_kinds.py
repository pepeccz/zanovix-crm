"""0505_activity_kinds

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-05-12 00:00:00.000000

Extends activity_log.kind CheckConstraint to add four new event kinds:
  ticket_opened, ticket_updated, ticket_closed, message_sent.

Existing values are preserved; downgrade restores the prior constraint set.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Prior kind values (as of 0002_crm_core_domain)
_PRIOR_KINDS = (
    "'stage_change','contact_added','contact_updated',"
    "'service_started','service_state_change','milestone_completed',"
    "'lead_converted','note'"
)

# Extended kind values (slice 5 additions)
_EXTENDED_KINDS = (
    "'stage_change','contact_added','contact_updated',"
    "'service_started','service_state_change','milestone_completed',"
    "'lead_converted','note',"
    "'ticket_opened','ticket_updated','ticket_closed','message_sent'"
)


def upgrade() -> None:
    # Drop the existing constraint, then recreate with extended set
    op.drop_constraint("ck_activity_log_kind", "activity_log", type_="check")
    op.create_check_constraint(
        "ck_activity_log_kind",
        "activity_log",
        f"kind IN ({_EXTENDED_KINDS})",
    )


def downgrade() -> None:
    # Restore the prior constraint (removes the 4 new kinds)
    op.drop_constraint("ck_activity_log_kind", "activity_log", type_="check")
    op.create_check_constraint(
        "ck_activity_log_kind",
        "activity_log",
        f"kind IN ({_PRIOR_KINDS})",
    )
