"""
BillingProfile Pydantic schemas (Pydantic v2).

Spain-focused billing identity — one per fiscal entity per client.
Tax-ID format validation runs in @model_validator so both tax_id and
tax_id_type are available simultaneously.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from api.schemas._tax_id_validators import (
    _validate_cif,
    _validate_nie,
    _validate_nif,
    _validate_vat,
)

# ---------------------------------------------------------------------------
# Allowed value sets (mirrors DB CHECK constraints)
# ---------------------------------------------------------------------------

TaxIdType = Literal["NIF", "CIF", "NIE", "VAT"]
TaxRegime = Literal[
    "general",
    "recargo_equivalencia",
    "simplificado",
    "exento",
    "intracomunitario",
]

_TAX_VALIDATORS = {
    "NIF": _validate_nif,
    "CIF": _validate_cif,
    "NIE": _validate_nie,
    "VAT": _validate_vat,
}


# ---------------------------------------------------------------------------
# Base (shared readable fields)
# ---------------------------------------------------------------------------


class BillingProfileBase(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    tax_id: str = Field(min_length=3, max_length=32)
    tax_id_type: TaxIdType
    tax_regime: TaxRegime
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    province: str = Field(min_length=1, max_length=120)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(default="ES", min_length=2, max_length=2)
    billing_email: EmailStr | None = None
    is_default: bool = False


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class BillingProfileCreate(BillingProfileBase):
    @field_validator("country")
    @classmethod
    def _country_upper(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _validate_tax_id(self) -> "BillingProfileCreate":
        _TAX_VALIDATORS[self.tax_id_type](self.tax_id)
        return self


# ---------------------------------------------------------------------------
# Update (partial — tax_id + tax_id_type must change together)
# ---------------------------------------------------------------------------


class BillingProfileUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    tax_id: str | None = Field(default=None, min_length=3, max_length=32)
    tax_id_type: TaxIdType | None = None
    tax_regime: TaxRegime | None = None
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    province: str | None = Field(default=None, min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, min_length=3, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    billing_email: EmailStr | None = None
    # is_default is intentionally NOT settable here — use PATCH /{id}/default

    @field_validator("country")
    @classmethod
    def _country_upper(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None

    @model_validator(mode="after")
    def _validate_if_paired(self) -> "BillingProfileUpdate":
        has_id = self.tax_id is not None
        has_type = self.tax_id_type is not None
        if has_id and has_type:
            _TAX_VALIDATORS[self.tax_id_type](self.tax_id)  # type: ignore[index]
        elif has_id ^ has_type:
            raise ValueError("tax_id and tax_id_type must be updated together")
        return self


# ---------------------------------------------------------------------------
# Read (response)
# ---------------------------------------------------------------------------


class BillingProfileRead(BillingProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
