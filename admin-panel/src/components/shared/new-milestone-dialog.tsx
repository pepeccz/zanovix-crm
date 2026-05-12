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

interface NewMilestoneDialogProps {
  serviceId: string;
  /** Current count of milestones — n defaults to count + 1 */
  existingCount: number;
  trigger?: React.ReactNode;
  onSuccess?: () => void;
}

export function NewMilestoneDialog({
  serviceId,
  existingCount,
  trigger,
  onSuccess,
}: NewMilestoneDialogProps) {
  const t = useTranslations("dialog.newMilestone");

  const [open, setOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [n, setN] = useState<string>(String(existingCount + 1));
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");

  function reset() {
    setN(String(existingCount + 1));
    setTitle("");
    setDueDate("");
  }

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (isOpen) {
      setN(String(existingCount + 1));
    } else {
      reset();
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.createMilestone(serviceId, {
        n: parseInt(n, 10),
        title: title.trim(),
        due_date: dueDate || undefined,
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
          <div className="grid grid-cols-[80px_1fr] gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="ms-n">{t("fields.n")}</Label>
              <Input
                id="ms-n"
                type="number"
                min="1"
                required
                value={n}
                onChange={(e) => setN(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-title">{t("fields.title")}</Label>
              <Input
                id="ms-title"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ms-due">{t("fields.due_date")}</Label>
            <Input
              id="ms-due"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
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
