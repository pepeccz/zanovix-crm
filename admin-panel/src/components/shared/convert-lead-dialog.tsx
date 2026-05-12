"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import api, { ApiError } from "@/lib/api";
import type { ClientStage, Lead } from "@/lib/types";

interface ConvertLeadDialogProps {
  lead: Lead;
  trigger?: React.ReactNode;
  onSuccess?: () => void;
}

const ALL_STAGES: ClientStage[] = [
  "lead",
  "discovery_scheduled",
  "discovery_done",
  "proposal_sent",
  "active",
  "lost",
];

export function ConvertLeadDialog({
  lead,
  trigger,
  onSuccess,
}: ConvertLeadDialogProps) {
  const t = useTranslations("dialog.convertLead");
  const tStatus = useTranslations("status");
  const router = useRouter();

  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [name, setName] = useState(lead.company || lead.name);
  const [sector, setSector] = useState("");
  const [size, setSize] = useState("");
  const [region, setRegion] = useState("");
  const [stage, setStage] = useState<ClientStage>("lead");
  const [mrrEuros, setMrrEuros] = useState("");

  function reset() {
    setName(lead.company || lead.name);
    setSector("");
    setSize("");
    setRegion("");
    setStage("lead");
    setMrrEuros("");
  }

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) reset();
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSaving(true);
    try {
      const mrrCents = mrrEuros
        ? Math.round(parseFloat(mrrEuros) * 100)
        : undefined;
      const created = await api.convertLead(lead.id, {
        name: name.trim() || undefined,
        sector: sector.trim() || undefined,
        size: size.trim() || undefined,
        region: region.trim() || undefined,
        stage,
        mrr_cents: mrrCents,
      });
      sileo.success({ title: t("success") });
      setOpen(false);
      onSuccess?.();
      router.push(`/clients/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          sileo.error({
            title: t("error"),
            description: t("alreadyConverted"),
          });
        } else if (err.status === 422) {
          sileo.error({
            title: t("error"),
            description: t("mustBeQualified"),
          });
        } else {
          sileo.error({ title: t("error"), description: err.message });
        }
      } else {
        sileo.error({
          title: t("error"),
          description: err instanceof Error ? err.message : undefined,
        });
      }
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-zx-ink-mute">{t("description")}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="conv-name">{t("fields.name")}</Label>
            <Input
              id="conv-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="conv-sector">{t("fields.sector")}</Label>
              <Input
                id="conv-sector"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="conv-size">{t("fields.size")}</Label>
              <Input
                id="conv-size"
                value={size}
                onChange={(e) => setSize(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="conv-region">{t("fields.region")}</Label>
              <Input
                id="conv-region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t("fields.stage")}</Label>
              <Select
                value={stage}
                onValueChange={(v) => setStage(v as ClientStage)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ALL_STAGES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {tStatus(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="conv-mrr">{t("fields.mrr")}</Label>
            <Input
              id="conv-mrr"
              type="number"
              step="0.01"
              min="0"
              value={mrrEuros}
              onChange={(e) => setMrrEuros(e.target.value)}
              placeholder="0.00"
            />
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
