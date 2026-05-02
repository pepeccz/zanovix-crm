"""
Payload sanitizer — builds the raw_payload JSONB snapshot stored on every Lead.

Design decisions (spec §7, design §6):
- Header allowlist is DEFAULT-DENY. Only User-Agent, Referer, X-Forwarded-For are kept.
- All other headers (Authorization, Cookie, X-Api-Key, etc.) are STRIPPED.
- Header matching is case-insensitive (HTTP headers are case-insensitive per RFC 7230).
- The client IP is hashed (sha256 + salt) before storage — never persisted in plaintext.
- ingested_at is captured in UTC ISO-8601 format.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import Request

from shared.config import get_settings

# Allowed headers stored in raw_payload (lowercase for case-insensitive matching)
HEADER_ALLOWLIST: frozenset[str] = frozenset({"user-agent", "referer", "x-forwarded-for"})


def build_raw_payload(request: Request, body: dict) -> dict:
    """
    Build a sanitized snapshot of the inbound request for storage in raw_payload.

    Args:
        request: The FastAPI Request object.
        body:    The already-parsed (and Pydantic-validated) request body as a dict.

    Returns:
        A dict safe to store in the JSONB raw_payload column:
        {
            "headers": { ... only allowed headers ... },
            "body": { ... original body fields ... },
            "ingested_at": "2026-05-02T12:00:00+00:00",
            "client_ip_hashed": "<sha256 hex>",
        }
    """
    filtered_headers = {
        k.lower(): v
        for k, v in request.headers.items()
        if k.lower() in HEADER_ALLOWLIST
    }

    return {
        "headers": filtered_headers,
        "body": body,
        "ingested_at": datetime.now(UTC).isoformat(),
        "client_ip_hashed": _hash_ip(_client_ip(request)),
    }


def _client_ip(request: Request) -> str:
    """
    Extract the client IP from the request.

    Reads X-Forwarded-For first (first value), falls back to direct remote address.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hash_ip(ip: str) -> str:
    """
    Hash an IP address using sha256 + configured salt.

    The raw IP is NEVER persisted. This one-way hash allows correlation
    (e.g. rate-limit debugging) without storing PII.
    """
    settings = get_settings()
    return hashlib.sha256(f"{ip}{settings.IP_HASH_SALT}".encode()).hexdigest()
