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
import type { ServiceRead, ServiceState } from "@/lib/types";
import { VALID_SERVICE_STATE_TRANSITIONS } from "@/lib/types";
import { StatusPill } from "@/components/shared/status-pill";
import { cn } from "@/lib/utils";

interface ServiceStateTransitionDialogProps {
  serviceId: string;
  currentState: ServiceState;
  onSuccess: (updated: ServiceRead) => void;
}

export function ServiceStateTransitionDialog({
  serviceId,
  currentState,
  onSuccess,
}: ServiceStateTransitionDialogProps) {
  const t = useTranslations("dialog.serviceStateTransition");
  const tStatus = useTranslations("status");

  const [open, setOpen] = useState(false);
  const [targetState, setTargetState] = useState<ServiceState | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  /**
   * When the server returns a 409 with an `allowed` list, we narrow the
   * displayed options to only those server-allowed states.
   */
  const [serverAllowed, setServerAllowed] = useState<ServiceState[] | null>(null);

  // Allowed transitions — server narrows if 409 was previously returned
  const allowedStates: ServiceState[] =
    serverAllowed ?? VALID_SERVICE_STATE_TRANSITIONS[currentState];

  function handleOpen(isOpen: boolean) {
    setOpen(isOpen);
    if (!isOpen) {
      // Reset on close
      setTargetState(null);
      setServerAllowed(null);
    }
  }

  async function handleConfirm() {
    if (!targetState) return;
    setIsSaving(true);
    try {
      const updated = await api.patchServiceState(serviceId, targetState);
      setOpen(false);
      onSuccess(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && Array.isArray(err.allowed)) {
        // Server returned narrowed allowed list — update state and keep dialog open
        setServerAllowed(err.allowed as ServiceState[]);
        // Reset selection if it's no longer in the allowed list
        if (targetState && !err.allowed.includes(targetState)) {
          setTargetState(null);
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

        {/* Current state indicator */}
        <div className="flex items-center gap-2 text-sm text-zx-ink-soft border-b border-zx-rule pb-3 mb-2">
          <span className="text-[11px] uppercase tracking-widest text-zx-ink-mute">
            Estado actual:
          </span>
          <StatusPill status={currentState} />
        </div>

        {/* State options */}
        {allowedStates.length === 0 ? (
          <p className="text-sm italic text-zx-ink-mute py-4 text-center">
            No hay transiciones disponibles para este estado.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {allowedStates.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setTargetState(s)}
                className={cn(
                  "flex items-center gap-3 rounded-md border px-4 py-2.5 text-left transition-all duration-100 cursor-pointer",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zx-green focus-visible:ring-offset-1",
                  targetState === s
                    ? "border-zx-ink bg-zx-ink/5"
                    : "border-zx-rule bg-transparent hover:border-zx-ink-soft"
                )}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                    targetState === s
                      ? "border-zx-ink bg-zx-ink"
                      : "border-zx-rule"
                  )}
                >
                  {targetState === s && (
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
            disabled={!targetState || isSaving}
          >
            {isSaving ? "Guardando..." : t("confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
