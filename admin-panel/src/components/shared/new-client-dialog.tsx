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
import api from "@/lib/api";
import type { ClientStage } from "@/lib/types";

interface NewClientDialogProps {
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

export function NewClientDialog({ onSuccess }: NewClientDialogProps) {
  const t = useTranslations("dialog.newClient");
  const tStatus = useTranslations("status");
  const router = useRouter();

  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [size, setSize] = useState("");
  const [region, setRegion] = useState("");
  const [stage, setStage] = useState<ClientStage>("lead");
  const [mrrEuros, setMrrEuros] = useState("");

  function reset() {
    setName("");
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
      const created = await api.createClient({
        name: name.trim(),
        sector: sector.trim() || undefined,
        size: size.trim() || undefined,
        region: region.trim() || undefined,
        stage,
        mrr_cents: mrrCents,
      });
      sileo.success({ title: t("success") });
      setOpen(false);
      reset();
      onSuccess?.();
      router.push(`/clients/${created.id}`);
    } catch (err) {
      sileo.error({
        title: t("error"),
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button>{t("trigger")}</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="client-name">{t("fields.name")}</Label>
            <Input
              id="client-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="client-sector">{t("fields.sector")}</Label>
              <Input
                id="client-sector"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="client-size">{t("fields.size")}</Label>
              <Input
                id="client-size"
                value={size}
                onChange={(e) => setSize(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="client-region">{t("fields.region")}</Label>
              <Input
                id="client-region"
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
            <Label htmlFor="client-mrr">{t("fields.mrr")}</Label>
            <Input
              id="client-mrr"
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
