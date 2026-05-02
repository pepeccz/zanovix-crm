"""
Lead status transition machine.

Enforces the valid transition graph for Lead.status. All business logic for
status transitions lives here — routes and services call assert_can_transition
and handle InvalidTransitionError.
"""

from __future__ import annotations


class InvalidTransitionError(Exception):
    """Raised when an attempted status transition is not permitted."""

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Cannot transition from '{from_status}' to '{to_status}'"
        )


class LeadStatusMachine:
    """
    Immutable finite-state machine for Lead.status.

    Terminal states (disqualified, converted) have empty target sets —
    any transition out of them raises InvalidTransitionError.
    """

    valid_transitions: dict[str, set[str]] = {
        "new": {"contacted", "disqualified"},
        "contacted": {"qualified", "disqualified"},
        "qualified": {"converted", "disqualified"},
        "disqualified": set(),  # terminal
        "converted": set(),  # terminal
    }

    @classmethod
    def assert_can_transition(cls, from_status: str, to_status: str) -> None:
        """
        Assert that the transition from_status → to_status is valid.

        Raises:
            InvalidTransitionError: if the transition is not in valid_transitions.
        """
        allowed = cls.valid_transitions.get(from_status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(from_status, to_status)
