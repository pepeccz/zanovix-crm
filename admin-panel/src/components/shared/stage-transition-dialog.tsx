"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { sileo } from "sileo";
import api, { ApiError } from "@/lib/api";
import type { ClientRead, ClientStage } from "@/lib/types";
import { VALID_CLIENT_STAGE_TRANSITIONS } from "@/lib/types";
import { StatusPill } from "@/components/shared/status-pill";
import { cn } from "@/lib/utils";

interface StageTransitionDialogProps {
  clientId: string;
  currentStage: ClientStage;
  onSuccess: (updated: ClientRead) => void;
}

export function StageTransitionDialog({
  clientId,
  currentStage,
  onSuccess,
}: StageTransitionDialogProps) {
  const t = useTranslations("dialog.stageTransition");
  const tStatus = useTranslations("status");

  const [open, setOpen] = useState(false);
  const [targetStage, setTargetStage] = useState<ClientStage | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  /**
   * When the server returns a 409 with an `allowed` list, we narrow the
   * displayed options to only those server-allowed stages.
   */
  const [serverAllowed, setServerAllowed] = useState<ClientStage[] | null>(null);

  // Allowed transitions — server narrows if 409 was previously returned
  const allowedStages: ClientStage[] =
    serverAllowed ?? VALID_CLIENT_STAGE_TRANSITIONS[currentStage];

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) {
      // Reset on close
      setTargetStage(null);
      setServerAllowed(null);
    }
  }

  async function handleConfirm() {
    if (!targetStage) return;
    setIsSaving(true);
    try {
      const updated = await api.patchClientStage(clientId, targetStage);
      setOpen(false);
      onSuccess(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && Array.isArray(err.allowed)) {
        // Server returned narrowed allowed list — update state and keep dialog open
        setServerAllowed(err.allowed as ClientStage[]);
        // Reset selection if it's no longer in the allowed list
        if (targetStage && !err.allowed.includes(targetStage)) {
          setTargetStage(null);
        }
        sileo.error({
          title: t("error"),
          description: err.message,
        });
      } else {
        sileo.error({
          title: t("error"),
          description: err instanceof Error ? err.message : "Error desconocido",
        });
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          {t("trigger")}
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
        </DialogHeader>

        <div className="py-2 text-sm text-zx-ink-mute">
          {t("description")}
        </div>

        {/* Current stage indicator */}
        <div className="flex items-center gap-2 text-sm text-zx-ink-soft border-b border-zx-rule pb-3 mb-2">
          <span className="text-[11px] uppercase tracking-widest text-zx-ink-mute">
            Etapa actual:
          </span>
          <StatusPill status={currentStage} />
        </div>

        {/* Stage options */}
        {allowedStages.length === 0 ? (
          <p className="text-sm italic text-zx-ink-mute py-4 text-center">
            No hay transiciones disponibles para esta etapa.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {allowedStages.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setTargetStage(s)}
                className={cn(
                  "flex items-center gap-3 rounded-md border px-4 py-2.5 text-left transition-all duration-100 cursor-pointer",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zx-green focus-visible:ring-offset-1",
                  targetStage === s
                    ? "border-zx-ink bg-zx-ink/5"
                    : "border-zx-rule bg-transparent hover:border-zx-ink-soft"
                )}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                    targetStage === s
                      ? "border-zx-ink bg-zx-ink"
                      : "border-zx-rule"
                  )}
                >
                  {targetStage === s && (
                    <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  )}
                </span>
                <StatusPill status={s} />
                <span className="sr-only">{tStatus(s)}</span>
              </button>
            ))}
          </div>
        )}

        <DialogFooter className="mt-4">
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isSaving}
          >
            {t("cancel")}
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!targetStage || isSaving}
          >
            {isSaving ? "Guardando..." : t("confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
