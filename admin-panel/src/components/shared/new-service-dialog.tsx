"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { sileo } from "sileo";
import api from "@/lib/api";
import type { ServiceType } from "@/lib/types";

interface NewServiceDialogProps {
  clientId: string;
  trigger?: React.ReactNode;
  onSuccess?: () => void;
}

const SERVICE_TYPES: ServiceType[] = ["assessment", "development", "formation"];

export function NewServiceDialog({
  clientId,
  trigger,
  onSuccess,
}: NewServiceDialogProps) {
  const t = useTranslations("dialog.newService");
  const tType = useTranslations("serviceType");

  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [type, setType] = useState<ServiceType>("assessment");
  const [setupEuros, setSetupEuros] = useState("");
  const [monthlyEuros, setMonthlyEuros] = useState("");

  function reset() {
    setTitle("");
    setType("assessment");
    setSetupEuros("");
    setMonthlyEuros("");
  }

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) reset();
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSaving(true);
    try {
      const setupCents = setupEuros
        ? Math.round(parseFloat(setupEuros) * 100)
        : undefined;
      const monthlyCents = monthlyEuros
        ? Math.round(parseFloat(monthlyEuros) * 100)
        : undefined;
      await api.createService(clientId, {
        title: title.trim(),
        type,
        setup_price_cents: setupCents,
        monthly_cents: monthlyCents,
      });
      sileo.success({ title: t("success") });
      setOpen(false);
      reset();
      onSuccess?.();
    } catch (err) {
      sileo.error({
        title: t("error"),
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setIsSaving(false);
    }
  }

  const triggerNode = trigger ?? (
    <Button variant="outline" size="sm">
      {t("trigger")}
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>{triggerNode}</DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="svc-title">{t("fields.title")}</Label>
            <Input
              id="svc-title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label>{t("fields.type")}</Label>
            <Select
              value={type}
              onValueChange={(v) => setType(v as ServiceType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SERVICE_TYPES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {tType(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="svc-setup">{t("fields.setup_price")}</Label>
              <Input
                id="svc-setup"
                type="number"
                step="0.01"
                min="0"
                value={setupEuros}
                onChange={(e) => setSetupEuros(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="svc-monthly">{t("fields.monthly")}</Label>
              <Input
                id="svc-monthly"
                type="number"
                step="0.01"
                min="0"
                value={monthlyEuros}
                onChange={(e) => setMonthlyEuros(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isSaving}
            >
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? t("saving") : t("submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
