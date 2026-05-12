"use client";

import { useState } from "react";
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import { useStageTransition } from "./use-stage-transition";
import type { ClientRead, ClientStage } from "@/lib/types";

/** The 5 pipeline stages in display order (excludes "lost"). */
const PIPELINE_STAGES: ClientStage[] = [
  "lead",
  "discovery_scheduled",
  "discovery_done",
  "proposal_sent",
  "active",
];

interface KanbanBoardProps {
  /** Full list of clients (pre-filtered by owner/sector if applicable). */
  clients: ClientRead[];
}

/**
 * KanbanBoard — top-level DnD container.
 *
 * Single DndContext per Design ADR-D3. Groups clients into 5 buckets by stage.
 * handleDragEnd: if dropped on a different stage column → optimistic update +
 * api.patchClientStage via useStageTransition hook.
 *
 * "lost" clients are excluded from the board (shown in list view instead).
 */
export function KanbanBoard({ clients: initialClients }: KanbanBoardProps) {
  const [clients, setClients] = useState<ClientRead[]>(initialClients);

  // Sync when the parent re-fetches (e.g. after filter change)
  // We use a key-based remount strategy at the page level for simplicity.
  // This component is intentionally uncontrolled after mount to keep
  // optimistic updates from flickering.

  const transition = useStageTransition(setClients);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // px — avoids accidental drag on click
      },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: 250,
        tolerance: 5,
      },
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;

    const clientId = active.id as string;
    const toStage = over.id as ClientStage;

    const client = clients.find((c) => c.id === clientId);
    if (!client) return;
    if (client.stage === toStage) return; // same column — no-op

    transition(clientId, toStage);
  }

  // Exclude "lost" clients — they're not part of the active pipeline board.
  const boardClients = clients.filter((c) => c.stage !== "lost");

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="grid border-t border-zx-rule" style={{ gridTemplateColumns: `repeat(${PIPELINE_STAGES.length}, 1fr)` }}>
        {PIPELINE_STAGES.map((stage, index) => (
          <KanbanColumn
            key={stage}
            stage={stage}
            clients={boardClients.filter((c) => c.stage === stage)}
            index={index}
          />
        ))}
      </div>
    </DndContext>
  );
}
