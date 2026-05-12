"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { sileo } from "sileo";
import api, { ApiError } from "@/lib/api";
import type { BillingProfile, BillingProfileCreate } from "@/lib/types";
import { BillingProfileForm, type BillingProfileFormErrors } from "./BillingProfileForm";

interface BillingProfileDialogProps {
  clientId: string;
  profile?: BillingProfile;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function BillingProfileDialog({
  clientId,
  profile,
  open,
  onOpenChange,
  onSuccess,
}: BillingProfileDialogProps) {
  const mode = profile ? "edit" : "create";
  const tCreate = useTranslations("dialog.newBillingProfile");
  const tEdit = useTranslations("dialog.editBillingProfile");
  const t = mode === "create" ? tCreate : tEdit;

  const [isSaving, setIsSaving] = useState(false);
  const [serverErrors, setServerErrors] = useState<BillingProfileFormErrors>({});

  async function handleSubmit(data: BillingProfileCreate) {
    setIsSaving(true);
    setServerErrors({});
    try {
      if (mode === "create") {
        await api.createBillingProfile(clientId, data);
      } else {
        await api.updateBillingProfile(profile!.id, data);
      }
      sileo.success({ title: t("success") });
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        // Unwrap nested billing_profile.tax_id path when coming from convert endpoint
        const raw = err.original as Record<string, unknown> | null;
        const detail = raw?.detail;
        if (Array.isArray(detail)) {
          const errors: BillingProfileFormErrors = {};
          for (const item of detail as Array<{ loc?: string[]; msg?: string }>) {
            if (item.loc && item.msg) {
              const field = item.loc[item.loc.length - 1];
              errors[field] = item.msg;
            }
          }
          if (Object.keys(errors).length > 0) {
            setServerErrors(errors);
            return;
          }
        }
      }
      sileo.error({
        title: t("error"),
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setIsSaving(false);
    }
  }

  const defaultValues = profile
    ? {
        legal_name: profile.legal_name,
        tax_id: profile.tax_id,
        tax_id_type: profile.tax_id_type,
        tax_regime: profile.tax_regime,
        address_line1: profile.address_line1,
        address_line2: profile.address_line2,
        city: profile.city,
        province: profile.province,
        postal_code: profile.postal_code,
        country: profile.country,
        billing_email: profile.billing_email,
      }
    : {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>
        <BillingProfileForm
          defaultValues={defaultValues}
          onSubmit={handleSubmit}
          mode={mode}
          isSaving={isSaving}
          serverErrors={serverErrors}
          onCancel={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}
