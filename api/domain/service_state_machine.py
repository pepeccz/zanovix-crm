"""
Service state transition machine.

Enforces the valid transition graph for Service.state. All business logic for
state transitions lives here — services call assert_can_transition and handle
InvalidTransitionError.

`completed` and `maintenance` are quasi-terminal (only completed → maintenance
is allowed out). `paused` is reachable from any non-terminal, non-completed
state and can resume to any of {scoping, running, review}.
"""

from __future__ import annotations

from api.domain.status_machine import InvalidTransitionError


class ServiceStateMachine:
    """
    Immutable finite-state machine for Service.state.

    valid_transitions maps each state to the set of reachable states.
    """

    valid_transitions: dict[str, set[str]] = {
        "scoping": {"running", "paused"},
        "running": {"review", "paused"},
        "review": {"completed", "paused"},
        "completed": {"maintenance"},
        "maintenance": set(),  # quasi-terminal
        "paused": {"scoping", "running", "review"},
    }

    @classmethod
    def assert_can_transition(cls, from_state: str, to_state: str) -> None:
        """
        Assert that the transition from_state → to_state is valid.

        Args:
            from_state: The current state of the service.
            to_state:   The desired target state.

        Raises:
            InvalidTransitionError: if the transition is not permitted.
        """
        allowed = cls.valid_transitions.get(from_state, set())
        if to_state not in allowed:
            raise InvalidTransitionError(from_state, to_state)
