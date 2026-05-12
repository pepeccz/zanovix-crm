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


# ---------------------------------------------------------------------------
# Client-domain exceptions (crm-core-domain slice)
# ---------------------------------------------------------------------------


class ClientNotFoundError(Exception):
    """Raised when a Client cannot be found, or is outside the user's ownership scope.

    Using a single exception for both cases prevents leaking client existence to
    unauthorized requesters — mirrors LeadNotFoundError pattern (spec REQ-14-C).
    """

    def __init__(self, client_id: object | None = None) -> None:
        self.client_id = client_id
        super().__init__(f"Client not found: {client_id}")


class ServiceNotFoundError(Exception):
    """Raised when a Service cannot be found, or the requester has no access to it.

    Consultor accessing another owner's service receives 404, not 403, to avoid
    leaking existence (spec REQ-14-C).
    """

    def __init__(self, service_id: object | None = None) -> None:
        self.service_id = service_id
        super().__init__(f"Service not found: {service_id}")


class ContactNotFoundError(Exception):
    """Raised when a Contact cannot be found under the given client."""

    def __init__(self, contact_id: object | None = None) -> None:
        self.contact_id = contact_id
        super().__init__(f"Contact not found: {contact_id}")


class MilestoneNotFoundError(Exception):
    """Raised when a Milestone cannot be found by (service_id, n)."""

    def __init__(self, service_id: object | None = None, n: object | None = None) -> None:
        self.service_id = service_id
        self.n = n
        super().__init__(f"Milestone not found: service={service_id}, n={n}")


class CannotCreateOnLostClientError(Exception):
    """Raised when attempting to create a Service under a client with stage='lost'.

    Maps to HTTP 422 with body {\"error\": \"client_is_lost\"} (spec REQ-16).
    """

    def __init__(self, client_id: object | None = None) -> None:
        self.client_id = client_id
        super().__init__(f"Cannot create service on a lost client: {client_id}")


class LeadAlreadyConvertedError(Exception):
    """Raised when a lead has already been converted to a client.

    Maps to HTTP 409 (spec REQ-13-C).
    """

    def __init__(self, lead_id: object | None = None, client_id: object | None = None) -> None:
        self.lead_id = lead_id
        self.client_id = client_id
        super().__init__(f"Lead {lead_id} already converted to client {client_id}")


class LeadNotQualifiedError(Exception):
    """Raised when a lead's status is not 'qualified' at conversion time.

    Maps to HTTP 422 with body {\"error\": \"lead_not_qualified\"} (spec REQ-13-B).
    """

    def __init__(self, lead_id: object | None = None, current_status: str | None = None) -> None:
        self.lead_id = lead_id
        self.current_status = current_status
        super().__init__(
            f"Lead {lead_id} is not qualified for conversion (status={current_status})"
        )


class RBACForbiddenError(Exception):
    """Raised when a user's role does not permit the requested action.

    Maps to HTTP 403. Distinct from 404-style existence-hiding — only raised when the
    resource exists and is visible but the verb is not permitted (e.g. consultor → create client).
    """

    def __init__(self, action: str | None = None, role: str | None = None) -> None:
        self.action = action
        self.role = role
        super().__init__(f"Role '{role}' is not permitted to perform '{action}'")


# ---------------------------------------------------------------------------
# Client-portal exceptions (crm-client-portal slice)
# ---------------------------------------------------------------------------


class TicketNotFoundError(Exception):
    """Raised when a Ticket is not found, or falls outside the caller's client_id scope.

    Using a single exception for both cases (not found + out-of-scope) is intentional:
    it prevents leaking ticket existence across client boundaries (spec §404-on-out-of-scope).
    Maps to HTTP 404.
    """

    def __init__(self, ticket_id: object | None = None) -> None:
        self.ticket_id = ticket_id
        super().__init__(f"Ticket not found: {ticket_id}")


class MessageNotFoundError(Exception):
    """Raised when a Message is not found, or falls outside the caller's client_id scope.

    Maps to HTTP 404 (same existence-hiding policy as TicketNotFoundError).
    """

    def __init__(self, message_id: object | None = None) -> None:
        self.message_id = message_id
        super().__init__(f"Message not found: {message_id}")


# ---------------------------------------------------------------------------
# Billing-profile exceptions (lead-role-billing-profiles slice)
# ---------------------------------------------------------------------------


class BillingProfileNotFoundError(Exception):
    """Raised when a BillingProfile cannot be found by the given ID.

    Maps to HTTP 404.
    """

    def __init__(self, profile_id: object | None = None) -> None:
        self.profile_id = profile_id
        super().__init__(f"Billing profile not found: {profile_id}")


class DuplicateTaxIdError(Exception):
    """Raised when a tax_id already exists for this client (unique per client).

    Maps to HTTP 409 Conflict — this is a state conflict, not a format error.
    """

    def __init__(self, client_id: object | None = None, tax_id: str | None = None) -> None:
        self.client_id = client_id
        self.tax_id = tax_id
        super().__init__(f"Duplicate tax_id '{tax_id}' for client {client_id}")


class CannotDeleteOnlyDefaultError(Exception):
    """Raised when deleting the only billing profile a client has.

    A client must always have at least one billing profile once created.
    Maps to HTTP 409 Conflict.
    """

    def __init__(self, profile_id: object | None = None) -> None:
        self.profile_id = profile_id
        super().__init__(f"Cannot delete the only billing profile: {profile_id}")
