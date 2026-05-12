"""
Unit tests for Spain-focused tax ID validators.

Tests are pure — no DB, no network. Each validator raises ValueError on invalid
input and returns None on valid input.
"""

from __future__ import annotations

import pytest

from api.schemas._tax_id_validators import (
    _validate_cif,
    _validate_nie,
    _validate_nif,
    _validate_vat,
)


# ---------------------------------------------------------------------------
# NIF — 8 digits + mod-23 control letter
# ---------------------------------------------------------------------------


class TestNifValidator:
    @pytest.mark.parametrize(
        "value",
        [
            "12345678Z",  # 12345678 % 23 = 14 → Z
            "00000000T",  # 0 % 23 = 0 → T
            "99999999R",  # 99999999 % 23 = 22 → R
            "12345674X",  # 12345674 % 23 = 10 → X
            "87654321X",  # 87654321 % 23 = 10 → X
        ],
    )
    def test_valid_nif(self, value: str) -> None:
        # Should not raise
        _validate_nif(value)

    @pytest.mark.parametrize(
        "value",
        [
            "12345678A",  # wrong letter (should be Z)
            "1234567Z",   # too short (7 digits)
            "123456789Z", # too long (9 digits)
            "1234567XZ",  # letter in digit portion
            "12345678",   # missing control letter
        ],
    )
    def test_invalid_nif(self, value: str) -> None:
        with pytest.raises(ValueError, match="invalid NIF"):
            _validate_nif(value)


# ---------------------------------------------------------------------------
# CIF — leading class letter + 7 digits + control digit or letter
# ---------------------------------------------------------------------------


class TestCifValidator:
    @pytest.mark.parametrize(
        "value",
        [
            "A1234567I",  # A is letter-control class; check_int=9 → I
            "B1234567I",  # B is digit-control class; check_int=9 → I (letter matches)
            "G12345679",  # G is digit-control class; check_int=9 → '9' as string
            "P1234567I",  # P is either-class; letter form accepted
        ],
    )
    def test_valid_cif(self, value: str) -> None:
        _validate_cif(value)

    @pytest.mark.parametrize(
        "value",
        [
            "A1234567A",  # wrong letter for class A (should be I)
            "B12345678",  # wrong digit for class B (should be 9 for 1234568, but 9 != 8)
            "Z1234567A",  # Z is not a valid CIF leading letter
            "A5827",      # too short
        ],
    )
    def test_invalid_cif(self, value: str) -> None:
        with pytest.raises(ValueError, match="invalid CIF"):
            _validate_cif(value)


# ---------------------------------------------------------------------------
# NIE — X/Y/Z prefix + 7 digits + NIF mod-23 letter
# ---------------------------------------------------------------------------


class TestNieValidator:
    def test_valid_nie_format_x1234567(self) -> None:
        # X→0, 01234567 % 23 = 20 → L
        _validate_nie("X1234567L")

    def test_nie_known_x_prefix(self) -> None:
        # X0000000T: 00000000 % 23 = 0 → T — valid
        _validate_nie("X0000000T")

    def test_valid_nie_y(self) -> None:
        # Y → 1, numeric = 10000000, 10000000 % 23 = 19 → Z
        _validate_nie("Y0000000Z")

    def test_valid_nie_z(self) -> None:
        # Z → 2, numeric = 20000000, 20000000 % 23 = 15 → M
        _validate_nie("Z0000000M")

    @pytest.mark.parametrize(
        "value",
        [
            "X0000000A",  # wrong letter (should be T)
            "A1234567L",  # A is not a valid NIE prefix
            "X123456L",   # too short (6 digits)
        ],
    )
    def test_invalid_nie(self, value: str) -> None:
        with pytest.raises(ValueError, match="invalid NIE"):
            _validate_nie(value)


# ---------------------------------------------------------------------------
# VAT — 2-letter ISO prefix + 2-12 alphanumeric (no VIES)
# ---------------------------------------------------------------------------


class TestVatValidator:
    @pytest.mark.parametrize(
        "value",
        [
            "ESB12345674",   # Spain CIF as VAT
            "FR12345678901", # France VAT
            "DE123456789",   # Germany VAT
        ],
    )
    def test_valid_vat(self, value: str) -> None:
        _validate_vat(value)

    @pytest.mark.parametrize(
        "value",
        [
            "ES1",            # too short (only 1 char after prefix)
            "E1234567890123", # prefix only 1 letter — fails regex
            "ES" + "A" * 13, # too long (13 chars after prefix, total 15)
            "1234567890",     # no letter prefix at all
        ],
    )
    def test_invalid_vat(self, value: str) -> None:
        with pytest.raises(ValueError, match="invalid VAT"):
            _validate_vat(value)
