"""
Unit tests for api/domain/service_state_machine.py.

Tests cover:
- All allowed transitions succeed (no exception).
- All forbidden transitions raise InvalidTransitionError.
- Happy path: scoping → running → review → completed → maintenance.
- Paused is reachable from every non-terminal state.
- Paused can resume to scoping / running / review.
- Completed → maintenance is the only exit from completed.
- maintenance is quasi-terminal (no outbound transitions).

No database involved — pure Python.
"""

from __future__ import annotations

import pytest

from api.domain.service_state_machine import ServiceStateMachine
from api.domain.status_machine import InvalidTransitionError

# ── Transition tables ──────────────────────────────────────────────────────────

ALLOWED_TRANSITIONS = [
    # Forward happy path
    ("scoping", "running"),
    ("running", "review"),
    ("review", "completed"),
    ("completed", "maintenance"),
    # Pause from any non-terminal, non-completed
    ("scoping", "paused"),
    ("running", "paused"),
    ("review", "paused"),
    # Resume from paused
    ("paused", "scoping"),
    ("paused", "running"),
    ("paused", "review"),
]

FORBIDDEN_TRANSITIONS = [
    # Cannot skip stages forward
    ("scoping", "review"),
    ("scoping", "completed"),
    ("scoping", "maintenance"),
    ("running", "completed"),
    ("running", "maintenance"),
    ("review", "maintenance"),
    # No backward movement (other than via paused resume)
    ("running", "scoping"),
    ("review", "running"),
    ("completed", "review"),
    ("maintenance", "completed"),
    # Cannot pause completed or maintenance
    ("completed", "paused"),
    ("maintenance", "paused"),
    # maintenance is fully terminal
    ("maintenance", "scoping"),
    ("maintenance", "running"),
    ("maintenance", "review"),
    # Paused cannot go directly to completed or maintenance
    ("paused", "completed"),
    ("paused", "maintenance"),
]


@pytest.mark.parametrize("from_state,to_state", ALLOWED_TRANSITIONS)
def test_allowed_transitions_do_not_raise(from_state: str, to_state: str) -> None:
    """Every edge in the valid_transitions graph must not raise."""
    ServiceStateMachine.assert_can_transition(from_state, to_state)


@pytest.mark.parametrize("from_state,to_state", FORBIDDEN_TRANSITIONS)
def test_forbidden_transitions_raise(from_state: str, to_state: str) -> None:
    """Every transition not in the graph must raise InvalidTransitionError."""
    with pytest.raises(InvalidTransitionError) as exc_info:
        ServiceStateMachine.assert_can_transition(from_state, to_state)

    err = exc_info.value
    assert err.from_status == from_state
    assert err.to_status == to_state


# ── Happy path sequence ────────────────────────────────────────────────────────

def test_happy_path_scoping_to_maintenance() -> None:
    """Full forward sequence: scoping → running → review → completed → maintenance."""
    path = ["scoping", "running", "review", "completed", "maintenance"]
    for from_state, to_state in zip(path, path[1:]):
        ServiceStateMachine.assert_can_transition(from_state, to_state)


# ── Paused behaviour ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("pauseable_state", ["scoping", "running", "review"])
def test_paused_reachable_from_non_terminal(pauseable_state: str) -> None:
    """Every non-terminal, non-completed state can enter paused."""
    ServiceStateMachine.assert_can_transition(pauseable_state, "paused")


@pytest.mark.parametrize("resume_target", ["scoping", "running", "review"])
def test_paused_can_resume_to_any_active_state(resume_target: str) -> None:
    """paused → {scoping, running, review} are all valid resume paths."""
    ServiceStateMachine.assert_can_transition("paused", resume_target)


def test_completed_cannot_be_paused() -> None:
    """completed → paused is forbidden (spec REQ-9-B)."""
    with pytest.raises(InvalidTransitionError) as exc_info:
        ServiceStateMachine.assert_can_transition("completed", "paused")

    assert exc_info.value.from_status == "completed"
    assert exc_info.value.to_status == "paused"


# ── Quasi-terminal states ──────────────────────────────────────────────────────

def test_maintenance_only_reachable_from_completed() -> None:
    """Only completed → maintenance is allowed; running → maintenance is not (spec REQ-9-C)."""
    # Valid path
    ServiceStateMachine.assert_can_transition("completed", "maintenance")

    # Invalid path
    with pytest.raises(InvalidTransitionError):
        ServiceStateMachine.assert_can_transition("running", "maintenance")


def test_maintenance_has_no_outbound_transitions() -> None:
    """maintenance is quasi-terminal — its valid_transitions set must be empty."""
    assert ServiceStateMachine.valid_transitions["maintenance"] == set()


def test_completed_exits_only_to_maintenance() -> None:
    """completed's only exit is maintenance — all other targets raise."""
    # Valid
    ServiceStateMachine.assert_can_transition("completed", "maintenance")

    # Invalid exits
    for bad_target in ("scoping", "running", "review", "paused"):
        with pytest.raises(InvalidTransitionError):
            ServiceStateMachine.assert_can_transition("completed", bad_target)


# ── Graph integrity ────────────────────────────────────────────────────────────

def test_all_states_present_in_graph() -> None:
    """All known state values must appear as keys in valid_transitions."""
    expected_states = {"scoping", "running", "review", "completed", "maintenance", "paused"}
    assert set(ServiceStateMachine.valid_transitions.keys()) == expected_states


def test_no_force_parameter_on_state_machine() -> None:
    """ServiceStateMachine.assert_can_transition does NOT accept a force parameter."""
    import inspect

    sig = inspect.signature(ServiceStateMachine.assert_can_transition)
    assert "force" not in sig.parameters, (
        "ServiceStateMachine must not have a force flag (spec REQ-9 has no force clause)"
    )
