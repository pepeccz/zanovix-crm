"""
Unit tests — ACTIVITY_KINDS constant (PR-4).

Spec §activity-log-kinds-enum-extension:
  The activity_log.kind MUST include all 8 original kinds (slice 1-4) PLUS the
  4 new kinds added in slice 5 (ticket_opened, ticket_updated, ticket_closed,
  message_sent). Total: 12 distinct values.

  The string CheckConstraint used in the DB migration (0505_activity_kinds.py)
  MUST exactly match the set of values in ACTIVITY_KINDS.

These tests serve as a regression guard: if someone adds or removes a kind in
the constant without updating the migration (or vice-versa), the test fails and
forces a conscious decision before the change is merged.
"""

from __future__ import annotations

from api.domain.activity_kinds import ACTIVITY_KINDS


# ---------------------------------------------------------------------------
# Expected sets (source of truth for these unit tests)
# ---------------------------------------------------------------------------

_SLICE_1_4_KINDS: frozenset[str] = frozenset(
    {
        "stage_change",
        "contact_added",
        "contact_updated",
        "service_started",
        "service_state_change",
        "milestone_completed",
        "lead_converted",
        "note",
    }
)

_SLICE_5_KINDS: frozenset[str] = frozenset(
    {
        "ticket_opened",
        "ticket_updated",
        "ticket_closed",
        "message_sent",
    }
)

_ALL_EXPECTED_KINDS: frozenset[str] = _SLICE_1_4_KINDS | _SLICE_5_KINDS

# ---------------------------------------------------------------------------
# CheckConstraint string as it appears in the 0505_activity_kinds migration.
# Tests below verify the migration constant matches ACTIVITY_KINDS exactly.
# ---------------------------------------------------------------------------

_MIGRATION_EXTENDED_KINDS_INLINE = (
    "'stage_change','contact_added','contact_updated',"
    "'service_started','service_state_change','milestone_completed',"
    "'lead_converted','note',"
    "'ticket_opened','ticket_updated','ticket_closed','message_sent'"
)


def _parse_migration_ck_string(ck_str: str) -> frozenset[str]:
    """Parse a comma-separated list of quoted SQL values into a Python set."""
    return frozenset(v.strip().strip("'") for v in ck_str.split(",") if v.strip())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActivityKindsConstant:
    def test_total_count_is_12(self) -> None:
        """ACTIVITY_KINDS must contain exactly 12 values (8 original + 4 new)."""
        assert len(ACTIVITY_KINDS) == 12, (
            f"Expected 12 kinds, got {len(ACTIVITY_KINDS)}: {sorted(ACTIVITY_KINDS)}"
        )

    def test_contains_all_slice_1_4_kinds(self) -> None:
        """All 8 original kinds from slices 1-4 must be present."""
        missing = _SLICE_1_4_KINDS - ACTIVITY_KINDS
        assert not missing, f"Missing slice 1-4 kinds: {missing}"

    def test_contains_all_slice_5_kinds(self) -> None:
        """All 4 new kinds introduced in slice 5 must be present."""
        missing = _SLICE_5_KINDS - ACTIVITY_KINDS
        assert not missing, f"Missing slice 5 kinds: {missing}"

    def test_no_unexpected_extra_kinds(self) -> None:
        """ACTIVITY_KINDS must not contain undocumented extra values."""
        unexpected = ACTIVITY_KINDS - _ALL_EXPECTED_KINDS
        assert not unexpected, (
            f"ACTIVITY_KINDS contains unexpected values not in spec: {unexpected}"
        )

    def test_is_frozenset(self) -> None:
        """ACTIVITY_KINDS must be a frozenset (immutable — prevents accidental mutation)."""
        assert isinstance(ACTIVITY_KINDS, frozenset), (
            f"Expected frozenset, got {type(ACTIVITY_KINDS)}"
        )

    def test_ticket_opened_present(self) -> None:
        assert "ticket_opened" in ACTIVITY_KINDS

    def test_ticket_updated_present(self) -> None:
        assert "ticket_updated" in ACTIVITY_KINDS

    def test_ticket_closed_present(self) -> None:
        assert "ticket_closed" in ACTIVITY_KINDS

    def test_message_sent_present(self) -> None:
        assert "message_sent" in ACTIVITY_KINDS


class TestMigrationCkStringMatchesConstant:
    """
    Cross-check that the CheckConstraint string in migration 0505 contains
    exactly the same set of values as ACTIVITY_KINDS.

    If these go out of sync (e.g. a kind is added to the constant but not the
    migration), the DB will accept inserts that the ORM constant rejects —
    a silent inconsistency that is very hard to debug in production.
    """

    def test_migration_ck_string_matches_activity_kinds(self) -> None:
        """Parse the migration CK string and compare to ACTIVITY_KINDS."""
        migration_kinds = _parse_migration_ck_string(_MIGRATION_EXTENDED_KINDS_INLINE)
        assert migration_kinds == ACTIVITY_KINDS, (
            f"Migration CheckConstraint kinds do not match ACTIVITY_KINDS.\n"
            f"  In migration but not constant: {migration_kinds - ACTIVITY_KINDS}\n"
            f"  In constant but not migration: {ACTIVITY_KINDS - migration_kinds}"
        )

    def test_migration_ck_has_12_values(self) -> None:
        """The migration CK string must also have exactly 12 values."""
        migration_kinds = _parse_migration_ck_string(_MIGRATION_EXTENDED_KINDS_INLINE)
        assert len(migration_kinds) == 12, (
            f"Migration CK has {len(migration_kinds)} values, expected 12: {sorted(migration_kinds)}"
        )

    def test_migration_file_ck_string_is_consistent(self) -> None:
        """
        Read the actual 0505_activity_kinds migration file and verify its
        _EXTENDED_KINDS string matches ACTIVITY_KINDS.

        This test imports the migration module directly — it will fail if the
        migration file is moved or renamed, which is intentional: the migration
        is the canonical source for the DB-level constraint.
        """
        import importlib.util
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parents[2]
            / "database"
            / "alembic"
            / "versions"
            / "f5a6b7c8d9e0_0505_activity_kinds.py"
        )
        spec = importlib.util.spec_from_file_location("migration_0505", migration_path)
        assert spec is not None and spec.loader is not None, (
            f"Could not load migration file at {migration_path}"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[arg-type]

        extended_kinds_str: str = module._EXTENDED_KINDS  # type: ignore[attr-defined]
        migration_kinds = _parse_migration_ck_string(extended_kinds_str)

        assert migration_kinds == ACTIVITY_KINDS, (
            f"_EXTENDED_KINDS in 0505 migration != ACTIVITY_KINDS constant.\n"
            f"  Migration has: {sorted(migration_kinds)}\n"
            f"  Constant has:  {sorted(ACTIVITY_KINDS)}"
        )
