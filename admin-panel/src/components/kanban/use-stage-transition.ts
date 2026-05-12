"use client";

import { useCallback, useRef, type Dispatch, type SetStateAction } from "react";
import { sileo } from "sileo";
import api, { ApiError } from "@/lib/api";
import type { ClientRead, ClientStage } from "@/lib/types";

/**
 * useStageTransition — optimistic update hook for kanban drag-and-drop.
 *
 * Immediately moves the card to the new column, calls patchClientStage,
 * and reverts on any error (409 shows allowed transitions; others show
 * a generic message).
 *
 * Design §6: single hook used only by KanbanBoard via handleDragEnd.
 */
export function useStageTransition(
  setClients: Dispatch<SetStateAction<ClientRead[]>>
) {
  // Captures the rollback function from the most recent optimistic update.
  const revertRef = useRef<(() => void) | null>(null);

  const transition = useCallback(
    async (id: string, toStage: ClientStage) => {
      // Snapshot current state for rollback, then apply optimistic update.
      let snapshot: ClientRead[] = [];

      setClients((prev) => {
        snapshot = prev;
        const next = prev.map((c) =>
          c.id === id ? { ...c, stage: toStage } : c
        );
        revertRef.current = () => setClients(snapshot);
        return next;
      });

      try {
        await api.patchClientStage(id, toStage);
        revertRef.current = null;
      } catch (err) {
        revertRef.current?.();
        revertRef.current = null;

        if (err instanceof ApiError && err.status === 409 && err.allowed) {
          sileo.error({
            title: "Cambio de etapa no permitido",
            description: `Transiciones permitidas: ${err.allowed.join(", ")}`,
          });
        } else {
          sileo.error({
            title: "No se pudo cambiar la etapa",
            description:
              err instanceof Error ? err.message : "Error desconocido",
          });
        }
      }
    },
    [setClients]
  );

  return transition;
}
