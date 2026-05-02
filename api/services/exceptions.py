"""
Domain exceptions for the service layer.

These exceptions are technology-agnostic — they carry no FastAPI or HTTP concepts.
The mapping to HTTP status codes lives in api/errors.py (error handler registration).
"""

from __future__ import annotations


class LeadNotFoundError(Exception):
    """Raised when a Lead cannot be found, or when it exists but is outside the user's scope.

    Using a single exception for both cases (not found + out-of-scope) is intentional:
    it prevents leaking lead existence to unauthorized requesters (spec §4 scenario 4.4).
    """

    def __init__(self, lead_id: object | None = None) -> None:
        self.lead_id = lead_id
        super().__init__(f"Lead not found: {lead_id}")


class InvalidTransitionError(Exception):
    """
    Raised when an attempted Lead status transition is not permitted.

    Re-exported here for convenience; the canonical definition is in
    api/domain/status_machine.py — import from there when working with
    the state machine directly.
    """

    def __init__(self, from_status: str, to_status: str, allowed_transitions: set[str]) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.allowed_transitions = allowed_transitions
        super().__init__(
            f"Cannot transition from '{from_status}' to '{to_status}'. "
            f"Allowed: {sorted(allowed_transitions)}"
        )


class RateLimitExceededError(Exception):
    """
    Raised when the rate limit for an endpoint is exceeded.

    retry_after_seconds: how many seconds the caller should wait before retrying.
    Consumed by Phase 4 rate limiter and optionally by api/errors.py → 429 handler.
    """

    def __init__(self, retry_after_seconds: int = 60) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s.")


class UnauthorizedLeadAccessError(Exception):
    """
    Raised when a consultor or comercial attempts to access a lead they don't own.

    This is intentionally returned as 404 (not 403) at the HTTP layer to avoid
    leaking lead existence to unauthorized requesters (spec §4 scenario 4.4).
    """

    def __init__(self, lead_id: object | None = None) -> None:
        self.lead_id = lead_id
        super().__init__(f"Unauthorized access to lead: {lead_id}")
