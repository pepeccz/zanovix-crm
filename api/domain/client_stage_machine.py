"""
Client stage transition machine.

Enforces the valid transition graph for Client.stage. All business logic for
stage transitions lives here — services call assert_can_transition and handle
InvalidTransitionError.

The `lost` stage is terminal. Passing force=True bypasses this restriction for
admin-layer escape hatches; callers are responsible for logging a warning.
"""

from __future__ import annotations

import logging

from api.domain.status_machine import InvalidTransitionError

logger = logging.getLogger(__name__)


class ClientStageMachine:
    """
    Immutable finite-state machine for Client.stage.

    valid_transitions maps each stage to the set of reachable stages.
    `lost` is terminal — its target set is empty unless force=True is passed.
    """

    valid_transitions: dict[str, set[str]] = {
        "lead": {"discovery_scheduled", "lost"},
        "discovery_scheduled": {"discovery_done", "lost"},
        "discovery_done": {"proposal_sent", "lost"},
        "proposal_sent": {"active", "lost"},
        "active": {"lost"},
        "lost": set(),  # terminal
    }

    @classmethod
    def assert_can_transition(
        cls,
        from_stage: str,
        to_stage: str,
        *,
        force: bool = False,
    ) -> None:
        """
        Assert that the transition from_stage → to_stage is valid.

        Args:
            from_stage: The current stage of the client.
            to_stage:   The desired target stage.
            force:      Admin-only override that allows transitions out of the
                        terminal `lost` stage. A warning is logged; no exception
                        is raised when force=True and from_stage is 'lost'.

        Raises:
            InvalidTransitionError: if the transition is not permitted.
        """
        if force and from_stage == "lost":
            logger.warning(
                "ForcedTransitionWarning: forced transition out of terminal "
                "stage 'lost' → '%s'. Proceeding by admin override.",
                to_stage,
            )
            return

        allowed = cls.valid_transitions.get(from_stage, set())
        if to_stage not in allowed:
            raise InvalidTransitionError(from_stage, to_stage)
