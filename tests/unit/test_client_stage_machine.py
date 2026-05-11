"""
Unit tests for api/domain/client_stage_machine.py.

Tests cover:
- All allowed transitions succeed (no exception).
- All forbidden transitions raise InvalidTransitionError.
- force=True bypasses the terminal 'lost' state.
- force=True is a no-op when the transition is already valid (defensive).

No database involved — pure Python.
"""

from __future__ import annotations

import pytest

from api.domain.client_stage_machine import ClientStageMachine
from api.domain.status_machine import InvalidTransitionError

# ── Allowed transitions ────────────────────────────────────────────────────────

ALLOWED_TRANSITIONS = [
    ("lead", "discovery_scheduled"),
    ("lead", "lost"),
    ("discovery_scheduled", "discovery_done"),
    ("discovery_scheduled", "lost"),
    ("discovery_done", "proposal_sent"),
    ("discovery_done", "lost"),
    ("proposal_sent", "active"),
    ("proposal_sent", "lost"),
    ("active", "lost"),
]

FORBIDDEN_TRANSITIONS = [
    # No backward movement
    ("discovery_scheduled", "lead"),
    ("discovery_done", "discovery_scheduled"),
    ("proposal_sent", "discovery_done"),
    ("active", "proposal_sent"),
    # No skipping forward
    ("lead", "proposal_sent"),
    ("lead", "active"),
    ("discovery_scheduled", "active"),
    # Terminal: no exit from lost (without force)
    ("lost", "lead"),
    ("lost", "active"),
    ("lost", "discovery_scheduled"),
]


@pytest.mark.parametrize("from_stage,to_stage", ALLOWED_TRANSITIONS)
def test_allowed_transitions_do_not_raise(from_stage: str, to_stage: str) -> None:
    """Every edge in the valid_transitions graph must not raise."""
    # No exception expected
    ClientStageMachine.assert_can_transition(from_stage, to_stage)


@pytest.mark.parametrize("from_stage,to_stage", FORBIDDEN_TRANSITIONS)
def test_forbidden_transitions_raise(from_stage: str, to_stage: str) -> None:
    """Every transition not in the graph must raise InvalidTransitionError."""
    with pytest.raises(InvalidTransitionError) as exc_info:
        ClientStageMachine.assert_can_transition(from_stage, to_stage)

    err = exc_info.value
    assert err.from_status == from_stage
    assert err.to_status == to_stage


# ── Terminal state (lost) ──────────────────────────────────────────────────────

def test_lost_is_terminal_without_force() -> None:
    """Transitioning out of 'lost' without force=True raises."""
    with pytest.raises(InvalidTransitionError) as exc_info:
        ClientStageMachine.assert_can_transition("lost", "lead")

    err = exc_info.value
    assert err.from_status == "lost"
    assert err.to_status == "lead"


@pytest.mark.parametrize("to_stage", ["lead", "discovery_scheduled", "active", "proposal_sent"])
def test_force_bypasses_lost_terminal(to_stage: str) -> None:
    """force=True allows exiting the 'lost' terminal state without raising."""
    # Must not raise
    ClientStageMachine.assert_can_transition("lost", to_stage, force=True)


def test_force_logs_warning_for_lost(caplog: pytest.LogCaptureFixture) -> None:
    """force=True on 'lost' emits a ForcedTransitionWarning log entry."""
    import logging

    with caplog.at_level(logging.WARNING, logger="api.domain.client_stage_machine"):
        ClientStageMachine.assert_can_transition("lost", "lead", force=True)

    assert any("ForcedTransitionWarning" in record.message for record in caplog.records)


def test_force_true_on_non_lost_normal_allowed_transition() -> None:
    """force=True on a normal (non-terminal) valid transition still succeeds."""
    # force is irrelevant for non-lost states but must not break valid transitions
    ClientStageMachine.assert_can_transition("lead", "discovery_scheduled", force=True)


def test_force_true_does_not_bypass_non_lost_forbidden() -> None:
    """force=True does NOT bypass invalid transitions from non-terminal states."""
    with pytest.raises(InvalidTransitionError):
        # 'lead' → 'active' is invalid even with force=True (force only applies to 'lost')
        ClientStageMachine.assert_can_transition("lead", "active", force=True)


# ── valid_transitions integrity ────────────────────────────────────────────────

def test_lost_has_empty_valid_transitions() -> None:
    """The 'lost' stage must have no outbound transitions in the graph."""
    assert ClientStageMachine.valid_transitions["lost"] == set()


def test_all_stages_present_in_graph() -> None:
    """All known stage values must appear as keys in valid_transitions."""
    expected_stages = {
        "lead",
        "discovery_scheduled",
        "discovery_done",
        "proposal_sent",
        "active",
        "lost",
    }
    assert set(ClientStageMachine.valid_transitions.keys()) == expected_stages
