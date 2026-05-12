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
import { sileo } from "sileo";
import api from "@/lib/api";

interface NewContactDialogProps {
  clientId: string;
  trigger?: React.ReactNode;
  onSuccess?: () => void;
}

export function NewContactDialog({
  clientId,
  trigger,
  onSuccess,
}: NewContactDialogProps) {
  const t = useTranslations("dialog.newContact");
  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);

  function reset() {
    setName("");
    setRole("");
    setEmail("");
    setPhone("");
    setIsPrimary(false);
  }

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) reset();
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.createContact(clientId, {
        client_id: clientId,
        name: name.trim(),
        role: role.trim() || undefined,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        is_primary: isPrimary,
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
            <Label htmlFor="contact-name">{t("fields.name")}</Label>
            <Input
              id="contact-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="contact-role">{t("fields.role")}</Label>
            <Input
              id="contact-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="contact-email">{t("fields.email")}</Label>
            <Input
              id="contact-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="contact-phone">{t("fields.phone")}</Label>
            <Input
              id="contact-phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-zx-ink cursor-pointer">
            <input
              type="checkbox"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
              className="h-4 w-4 rounded border-zx-rule"
            />
            {t("fields.is_primary")}
          </label>

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
