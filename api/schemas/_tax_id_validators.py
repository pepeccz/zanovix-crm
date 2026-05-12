"""
Spain-focused tax ID format validators.

Each function receives the raw string and raises ``ValueError`` if the format is
invalid. Pydantic's ``@field_validator`` / ``@model_validator`` will surface these
as HTTP 422 Unprocessable Entity responses with the validator's message.

References:
  NIF — BOE-A-2008-10152 (Orden EHA/3434/2007)
  CIF — BOE-A-1976-12162 (Decreto 2423/1975), updated by RD 1065/2007 art.18
  NIE — same letter table as NIF with X→0/Y→1/Z→2 prefix substitution
  VAT — EC Council Directive 2006/112/EC art.214; format check only (no VIES)
"""

from __future__ import annotations

import re

_NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"

_NIF_RE = re.compile(r"^[0-9]{8}[A-Z]$")
_CIF_RE = re.compile(r"^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$")
_NIE_RE = re.compile(r"^[XYZ][0-9]{7}[A-Z]$")
_VAT_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2,12}$")

# CIF leading-letter → expected control character class
# Group 1: letter control (A, B, E, H)  — leading chars that require a letter
# Group 2: digit control (C, D, G, J, U, V, W)
# Group 3: either (N, P, Q, R, S)
_CIF_LETTER_CONTROL_CHARS = set("ABEH")
_CIF_DIGIT_CONTROL_CHARS = set("CDGJUVW")
_CIF_EITHER_CONTROL_CHARS = set("FNPQRS")

_CIF_CONTROL_LETTERS = "JABCDEFGHI"


def _validate_nif(value: str) -> None:
    """Validate a Spanish NIF (8 digits + control letter, mod-23 table)."""
    v = value.strip().upper()
    if not _NIF_RE.match(v):
        raise ValueError("invalid NIF")
    digits = int(v[:8])
    expected = _NIF_LETTERS[digits % 23]
    if v[8] != expected:
        raise ValueError("invalid NIF")


def _cif_check_digit(seven_digits: str) -> tuple[int, str]:
    """
    Compute the CIF Luhn-like check over the 7 middle digits.

    Returns (check_digit_int, check_letter) so the caller can validate
    against either the digit or the letter form of the control character.
    """
    odd_sum = sum(int(seven_digits[i]) for i in (0, 2, 4, 6))
    even_sum = 0
    for i in (1, 3, 5):
        doubled = int(seven_digits[i]) * 2
        even_sum += doubled // 10 + doubled % 10
    total = odd_sum + even_sum
    check_int = (10 - (total % 10)) % 10
    return check_int, _CIF_CONTROL_LETTERS[check_int]


def _validate_cif(value: str) -> None:
    """
    Validate a Spanish CIF.

    Format: one letter (A-H, J, N-S, U-W) + 7 digits + control (digit or letter).
    The control character type depends on the leading letter:
      - A, B, E, H → must be a letter (A–J)
      - C, D, G, J, U, V, W → must be a digit (0–9)
      - F, N, P, Q, R, S → either digit or letter accepted
    """
    v = value.strip().upper()
    if not _CIF_RE.match(v):
        raise ValueError("invalid CIF")

    leading = v[0]
    seven = v[1:8]
    control = v[8]
    check_int, check_letter = _cif_check_digit(seven)

    if leading in _CIF_LETTER_CONTROL_CHARS:
        if control != check_letter:
            raise ValueError("invalid CIF")
    elif leading in _CIF_DIGIT_CONTROL_CHARS:
        if control != str(check_int):
            raise ValueError("invalid CIF")
    else:
        # Either form is valid
        if control != check_letter and control != str(check_int):
            raise ValueError("invalid CIF")


def _validate_nie(value: str) -> None:
    """
    Validate a Spanish NIE (X/Y/Z prefix + 7 digits + NIF control letter).

    Prefix substitution: X→0, Y→1, Z→2; then apply NIF mod-23 on the resulting
    8-digit string.
    """
    v = value.strip().upper()
    if not _NIE_RE.match(v):
        raise ValueError("invalid NIE")
    prefix_map = {"X": "0", "Y": "1", "Z": "2"}
    numeric_str = prefix_map[v[0]] + v[1:8]
    digits = int(numeric_str)
    expected = _NIF_LETTERS[digits % 23]
    if v[8] != expected:
        raise ValueError("invalid NIE")


def _validate_vat(value: str) -> None:
    """
    Validate an EU VAT number (format check only — no VIES lookup).

    Expected: 2-letter ISO country prefix + 2–12 alphanumeric characters.
    All characters must be uppercase ASCII.
    """
    v = value.strip().upper()
    if not _VAT_RE.match(v):
        raise ValueError("invalid VAT")
