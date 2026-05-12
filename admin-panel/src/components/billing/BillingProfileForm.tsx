"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { BillingProfileCreate, TaxIdType, TaxRegime } from "@/lib/types";

const TAX_ID_TYPES: TaxIdType[] = ["NIF", "CIF", "NIE", "VAT"];
const TAX_REGIMES: TaxRegime[] = [
  "general",
  "recargo_equivalencia",
  "simplificado",
  "exento",
  "intracomunitario",
];

export interface BillingProfileFormErrors {
  [field: string]: string;
}

interface BillingProfileFormProps {
  defaultValues?: Partial<BillingProfileCreate>;
  onSubmit: (data: BillingProfileCreate) => void;
  /**
   * Fires whenever any field changes with the current partial form data.
   * Useful for parent forms that want to track billing data live without
   * waiting for an explicit form submit.
   */
  onChange?: (data: Partial<BillingProfileCreate>) => void;
  mode: "create" | "edit";
  isSaving: boolean;
  serverErrors?: BillingProfileFormErrors;
  onCancel?: () => void;
  submitLabel?: string;
  cancelLabel?: string;
  /** When true, the action buttons row is not rendered */
  hideActions?: boolean;
}

export function BillingProfileForm({
  defaultValues = {},
  onSubmit,
  onChange,
  mode,
  isSaving,
  serverErrors = {},
  onCancel,
  submitLabel,
  cancelLabel,
  hideActions = false,
}: BillingProfileFormProps) {
  const t = useTranslations("dialog.billingProfileForm");
  const tCreate = useTranslations("dialog.newBillingProfile");
  const tEdit = useTranslations("dialog.editBillingProfile");

  const [legalName, setLegalName] = useState(defaultValues.legal_name ?? "");
  const [taxIdType, setTaxIdType] = useState<TaxIdType>(
    defaultValues.tax_id_type ?? "NIF"
  );
  const [taxId, setTaxId] = useState(defaultValues.tax_id ?? "");
  const [taxRegime, setTaxRegime] = useState<TaxRegime>(
    defaultValues.tax_regime ?? "general"
  );
  const [addressLine1, setAddressLine1] = useState(
    defaultValues.address_line1 ?? ""
  );
  const [addressLine2, setAddressLine2] = useState(
    defaultValues.address_line2 ?? ""
  );
  const [city, setCity] = useState(defaultValues.city ?? "");
  const [province, setProvince] = useState(defaultValues.province ?? "");
  const [postalCode, setPostalCode] = useState(defaultValues.postal_code ?? "");
  const [country, setCountry] = useState(defaultValues.country ?? "ES");
  const [billingEmail, setBillingEmail] = useState(
    defaultValues.billing_email ?? ""
  );

  function buildCurrent(overrides: Partial<{
    legalName: string; taxId: string; taxIdType: TaxIdType; taxRegime: TaxRegime;
    addressLine1: string; addressLine2: string; city: string; province: string;
    postalCode: string; country: string; billingEmail: string;
  }> = {}): BillingProfileCreate {
    const ln = overrides.legalName ?? legalName;
    const ti = overrides.taxId ?? taxId;
    const tit = overrides.taxIdType ?? taxIdType;
    const tr = overrides.taxRegime ?? taxRegime;
    const a1 = overrides.addressLine1 ?? addressLine1;
    const a2 = overrides.addressLine2 ?? addressLine2;
    const c = overrides.city ?? city;
    const pv = overrides.province ?? province;
    const pc = overrides.postalCode ?? postalCode;
    const co = overrides.country ?? country;
    const be = overrides.billingEmail ?? billingEmail;
    return {
      legal_name: ln.trim(),
      tax_id: ti.trim().toUpperCase(),
      tax_id_type: tit,
      tax_regime: tr,
      address_line1: a1.trim(),
      address_line2: a2.trim() || null,
      city: c.trim(),
      province: pv.trim(),
      postal_code: pc.trim(),
      country: co.trim().toUpperCase() || "ES",
      billing_email: be.trim() || null,
    };
  }

  function notifyChange(overrides: Parameters<typeof buildCurrent>[0] = {}) {
    onChange?.(buildCurrent(overrides));
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSubmit(buildCurrent());
  }

  const resolvedSubmitLabel =
    submitLabel ?? (mode === "create" ? tCreate("submit") : tEdit("submit"));
  const resolvedCancelLabel = cancelLabel ?? tCreate("cancel");

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Legal name */}
      <div className="space-y-1.5">
        <Label htmlFor="bp-legal-name">{t("fields.legal_name")}</Label>
        <Input
          id="bp-legal-name"
          required
          maxLength={255}
          value={legalName}
          onChange={(e) => { setLegalName(e.target.value); notifyChange({ legalName: e.target.value }); }}
        />
      </div>

      {/* Tax ID type + Tax ID */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>{t("fields.tax_id_type")}</Label>
          <Select
            value={taxIdType}
            onValueChange={(v) => { setTaxIdType(v as TaxIdType); notifyChange({ taxIdType: v as TaxIdType }); }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TAX_ID_TYPES.map((v) => (
                <SelectItem key={v} value={v}>
                  {t(`tax_id_type.${v}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bp-tax-id">{t("fields.tax_id")}</Label>
          <Input
            id="bp-tax-id"
            required
            maxLength={32}
            value={taxId}
            onChange={(e) => { setTaxId(e.target.value); notifyChange({ taxId: e.target.value }); }}
            aria-invalid={!!serverErrors.tax_id}
          />
          {serverErrors.tax_id && (
            <p className="text-xs text-destructive">{serverErrors.tax_id}</p>
          )}
        </div>
      </div>

      {/* Tax regime */}
      <div className="space-y-1.5">
        <Label>{t("fields.tax_regime")}</Label>
        <Select
          value={taxRegime}
          onValueChange={(v) => { setTaxRegime(v as TaxRegime); notifyChange({ taxRegime: v as TaxRegime }); }}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TAX_REGIMES.map((r) => (
              <SelectItem key={r} value={r}>
                {t(`tax_regime.${r}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Address */}
      <div className="space-y-1.5">
        <Label htmlFor="bp-addr1">{t("fields.address_line1")}</Label>
        <Input
          id="bp-addr1"
          required
          maxLength={255}
          value={addressLine1}
          onChange={(e) => { setAddressLine1(e.target.value); notifyChange({ addressLine1: e.target.value }); }}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="bp-addr2">{t("fields.address_line2")}</Label>
        <Input
          id="bp-addr2"
          maxLength={255}
          value={addressLine2}
          onChange={(e) => { setAddressLine2(e.target.value); notifyChange({ addressLine2: e.target.value }); }}
        />
      </div>

      {/* City + Province */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="bp-city">{t("fields.city")}</Label>
          <Input
            id="bp-city"
            required
            maxLength={120}
            value={city}
            onChange={(e) => { setCity(e.target.value); notifyChange({ city: e.target.value }); }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bp-province">{t("fields.province")}</Label>
          <Input
            id="bp-province"
            required
            maxLength={120}
            value={province}
            onChange={(e) => { setProvince(e.target.value); notifyChange({ province: e.target.value }); }}
          />
        </div>
      </div>

      {/* Postal code + Country */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="bp-postal">{t("fields.postal_code")}</Label>
          <Input
            id="bp-postal"
            required
            maxLength={20}
            value={postalCode}
            onChange={(e) => { setPostalCode(e.target.value); notifyChange({ postalCode: e.target.value }); }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bp-country">{t("fields.country")}</Label>
          <Input
            id="bp-country"
            required
            maxLength={2}
            minLength={2}
            value={country}
            onChange={(e) => { setCountry(e.target.value); notifyChange({ country: e.target.value }); }}
          />
        </div>
      </div>

      {/* Billing email */}
      <div className="space-y-1.5">
        <Label htmlFor="bp-email">{t("fields.billing_email")}</Label>
        <Input
          id="bp-email"
          type="email"
          maxLength={255}
          value={billingEmail}
          onChange={(e) => { setBillingEmail(e.target.value); notifyChange({ billingEmail: e.target.value }); }}
        />
      </div>

      {/* Actions */}
      {!hideActions && (
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSaving}
          >
            {resolvedCancelLabel}
          </Button>
        )}
        <Button type="submit" disabled={isSaving}>
          {isSaving
            ? mode === "create"
              ? tCreate("saving")
              : tEdit("saving")
            : resolvedSubmitLabel}
        </Button>
      </div>
      )}
    </form>
  );
}
