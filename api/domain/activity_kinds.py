"""Activity log kind constants — single source of truth for the kind whitelist.

Both the ORM CheckConstraint and the activity_log_service runtime assertion
reference this set (ADR-10: defense in depth).
"""

from __future__ import annotations

ACTIVITY_KINDS: frozenset[str] = frozenset(
    {
        # Slice 1-4 kinds
        "stage_change",
        "contact_added",
        "contact_updated",
        "service_started",
        "service_state_change",
        "milestone_completed",
        "lead_converted",
        "note",
        # Slice 5 — client portal additions
        "ticket_opened",
        "ticket_updated",
        "ticket_closed",
        "message_sent",
    }
)
