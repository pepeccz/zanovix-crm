"""
Integration tests — Alembic migration downgrade round-trip (PR-4).

Spec §alembic-downgrade-test (W02):
  The suite MUST include at least one test that applies the slice-5 migration
  chain and then calls alembic downgrade in reverse, asserting the DB reaches
  the pre-slice schema without error.

Strategy:
  1. The full migration chain is already applied by the time tests run.
  2. This test downgrades the five slice-5 migrations one-by-one (in reverse).
  3. After each downgrade, it asserts the corresponding table/column is absent.
  4. Then it re-applies (upgrade head) and asserts the schema is restored.

WARNING — SCHEMA MUTATION TEST:
  This test modifies the actual test-DB schema. It is designed to be safe
  because it always ends with ``upgrade head``, but it MUST NOT run concurrently
  with other integration tests that depend on the live schema.

  Set the environment variable SKIP_SCHEMA_MUTATION_TESTS=1 to skip this test
  in environments where schema changes are not allowed (e.g. shared CI runners).
  Mark the entire module with pytest.mark.schema_mutation so it can be filtered
  with ``pytest -m 'not schema_mutation'`` as an alternative.
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, create_engine

# ---------------------------------------------------------------------------
# Conditional skip
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.schema_mutation

_SKIP = os.getenv("SKIP_SCHEMA_MUTATION_TESTS", "0") == "1"


def _make_alembic_cfg(db_url: str) -> Config:
    """Build an Alembic Config object pointing at the project alembic.ini."""
    cfg = Config("alembic.ini")
    # Alembic requires synchronous URL; convert asyncpg → psycopg
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


def _sync_engine(db_url: str) -> Engine:
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    return create_engine(sync_url, echo=False)


def _table_exists(engine: Engine, table_name: str) -> bool:
    insp = inspect(engine)
    return insp.has_table(table_name)


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return False
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


# ---------------------------------------------------------------------------
# Slice-5 revision IDs (in upgrade order)
# ---------------------------------------------------------------------------

_SLICE5_REVISIONS = [
    "b1c2d3e4f5a6",  # 0501_client_portal_auth  — users.client_id + role CK
    "c2d3e4f5a6b7",  # 0502_tickets             — tickets table
    "d3e4f5a6b7c8",  # 0503_messages            — messages table
    "e4f5a6b7c8d9",  # 0504_diagnostic_json     — services.diagnostic_json
    "f5a6b7c8d9e0",  # 0505_activity_kinds      — CK swap for activity_log.kind
]

# The revision that was head BEFORE slice-5 (end of slice 1-4 chain)
_PRE_SLICE5_HEAD = "a1b2c3d4e5f6"


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason="SKIP_SCHEMA_MUTATION_TESTS=1 is set")
def test_slice5_downgrade_and_reapply() -> None:
    """
    Downgrade all 5 slice-5 migrations in reverse order, then upgrade head.

    Assertions after each downgrade step confirm the expected schema changes
    are correctly reverted. Final upgrade brings the schema back to full head.
    """
    from shared.config import get_settings

    settings = get_settings()
    cfg = _make_alembic_cfg(settings.DATABASE_URL)
    engine = _sync_engine(settings.DATABASE_URL)

    try:
        # ── Step 1: downgrade 0505 (activity_kinds CK swap) ─────────────────
        # After downgrade the CK is restored to the prior set; activity_log
        # table must still exist (only constraint changes, not table structure).
        command.downgrade(cfg, "e4f5a6b7c8d9")  # target = 0504 (one step back from 0505)
        assert _table_exists(engine, "activity_log"), "activity_log table should still exist after 0505 downgrade"

        # ── Step 2: downgrade 0504 (diagnostic_json column removed) ─────────
        command.downgrade(cfg, "d3e4f5a6b7c8")  # target = 0503
        assert not _column_exists(engine, "services", "diagnostic_json"), (
            "services.diagnostic_json should be absent after 0504 downgrade"
        )

        # ── Step 3: downgrade 0503 (messages table dropped) ─────────────────
        command.downgrade(cfg, "c2d3e4f5a6b7")  # target = 0502
        assert not _table_exists(engine, "messages"), (
            "messages table should be absent after 0503 downgrade"
        )

        # ── Step 4: downgrade 0502 (tickets table dropped) ──────────────────
        command.downgrade(cfg, "b1c2d3e4f5a6")  # target = 0501
        assert not _table_exists(engine, "tickets"), (
            "tickets table should be absent after 0502 downgrade"
        )

        # ── Step 5: downgrade 0501 (users.client_id removed + role CK restored)
        command.downgrade(cfg, _PRE_SLICE5_HEAD)  # target = 0002
        assert not _column_exists(engine, "users", "client_id"), (
            "users.client_id should be absent after 0501 downgrade"
        )

        # ── Step 6: re-apply all slice-5 migrations ──────────────────────────
        command.upgrade(cfg, "head")
        assert _table_exists(engine, "tickets"), "tickets table should exist after upgrade head"
        assert _table_exists(engine, "messages"), "messages table should exist after upgrade head"
        assert _column_exists(engine, "services", "diagnostic_json"), (
            "services.diagnostic_json should exist after upgrade head"
        )
        assert _column_exists(engine, "users", "client_id"), (
            "users.client_id should exist after upgrade head"
        )

    finally:
        # Safety net: ensure we always end at head, even if an assertion fails.
        # This prevents the test DB from being left in a partially-downgraded
        # state that would break subsequent tests.
        try:
            command.upgrade(cfg, "head")
        except Exception:
            pass  # Already at head or can't recover — nothing more to do here.
        engine.dispose()


@pytest.mark.skipif(_SKIP, reason="SKIP_SCHEMA_MUTATION_TESTS=1 is set")
def test_single_step_downgrade_upgrade_0505() -> None:
    """
    Smoke test: downgrade just the last migration (-1) then re-apply.

    This is the minimal round-trip that confirms alembic downgrade -1 works
    from the current head without touching any other migration.
    """
    from shared.config import get_settings

    settings = get_settings()
    cfg = _make_alembic_cfg(settings.DATABASE_URL)
    engine = _sync_engine(settings.DATABASE_URL)

    try:
        # downgrade -1 (from head = f5a6b7c8d9e0 to e4f5a6b7c8d9)
        command.downgrade(cfg, "-1")
        # activity_log still exists; just the CK changed
        assert _table_exists(engine, "activity_log")

        # Re-apply
        command.upgrade(cfg, "head")
        assert _table_exists(engine, "activity_log")

    finally:
        try:
            command.upgrade(cfg, "head")
        except Exception:
            pass
        engine.dispose()
