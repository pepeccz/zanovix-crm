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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { sileo } from "sileo";
import api from "@/lib/api";
import type { LeadChannel, LeadVertical } from "@/lib/types";

interface NewLeadDialogProps {
  onSuccess?: () => void;
}

const VERTICALS: LeadVertical[] = ["clinicas_dentales", "general"];
const CHANNELS: LeadChannel[] = [
  "email_marketing",
  "cold_calling",
  "networking",
  "referral",
  "web_form",
  "other",
];

export function NewLeadDialog({ onSuccess }: NewLeadDialogProps) {
  const t = useTranslations("dialog.newLead");
  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [vertical, setVertical] = useState<LeadVertical>("general");
  const [channel, setChannel] = useState<LeadChannel>("web_form");
  const [notes, setNotes] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");

  function reset() {
    setName("");
    setEmail("");
    setPhone("");
    setCompany("");
    setVertical("general");
    setChannel("web_form");
    setNotes("");
    setSourceUrl("");
  }

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) reset();
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.createLead({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        company: company.trim() || undefined,
        vertical,
        channel,
        notes: notes.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
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
            <Label htmlFor="lead-name">{t("fields.name")}</Label>
            <Input
              id="lead-name"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="lead-email">{t("fields.email")}</Label>
            <Input
              id="lead-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="lead-phone">{t("fields.phone")}</Label>
              <Input
                id="lead-phone"
                maxLength={50}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-company">{t("fields.company")}</Label>
              <Input
                id="lead-company"
                maxLength={200}
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>{t("fields.vertical")}</Label>
              <Select
                value={vertical}
                onValueChange={(v) => setVertical(v as LeadVertical)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VERTICALS.map((v) => (
                    <SelectItem key={v} value={v}>
                      {t(`vertical.${v}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>{t("fields.channel")}</Label>
              <Select
                value={channel}
                onValueChange={(v) => setChannel(v as LeadChannel)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHANNELS.map((c) => (
                    <SelectItem key={c} value={c}>
                      {t(`channel.${c}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="lead-source">{t("fields.source_url")}</Label>
            <Input
              id="lead-source"
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="lead-notes">{t("fields.notes")}</Label>
            <Textarea
              id="lead-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
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
