"use client";

import { useDroppable } from "@dnd-kit/core";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { KanbanCard } from "./kanban-card";
import type { ClientRead, ClientStage } from "@/lib/types";

interface KanbanColumnProps {
  stage: ClientStage;
  clients: ClientRead[];
  /** Zero-based column index for visual numbering */
  index: number;
}

/**
 * KanbanColumn — droppable column for a single pipeline stage.
 *
 * useDroppable id = stage string (same key used in handleDragEnd).
 * Design: zx-paper-2 background, border-zx-rule, min-height for empty columns.
 * Header shows stage label + count. Body is a vertical stack of KanbanCards.
 */
export function KanbanColumn({ stage, clients, index }: KanbanColumnProps) {
  const t = useTranslations("stage");
  const tEmpty = useTranslations("page.pipeline");

  const { isOver, setNodeRef } = useDroppable({ id: stage });

  const isActive = stage === "active";

  return (
    <div
      className={cn(
        "flex flex-col border-r border-zx-rule last:border-r-0 min-h-[calc(100vh-280px)]",
        isActive && "bg-zx-green/[0.03]"
      )}
    >
      {/* Column header */}
      <div className="px-4 py-3 border-b border-zx-rule bg-zx-paper-2/60 flex items-baseline justify-between shrink-0">
        <div>
          <p
            className="font-serif italic text-[12px] text-zx-green mb-0.5"
            style={{ fontFamily: "Newsreader, serif" }}
          >
            — Fase {String(index + 1).padStart(2, "0")}
          </p>
          <p
            className="font-serif font-medium text-[16px] text-zx-ink tracking-[-0.01em]"
            style={{ fontFamily: "Newsreader, serif" }}
          >
            {t(stage)}
          </p>
        </div>

        <span className="font-sans text-[11px] text-zx-ink-mute tabular-nums text-right">
          {clients.length}
        </span>
      </div>

      {/* Droppable card area */}
      <div
        ref={setNodeRef}
        className={cn(
          "flex-1 flex flex-col gap-2 p-2.5 transition-colors duration-150",
          isOver && "bg-zx-green/[0.06]"
        )}
      >
        {clients.map((client) => (
          <KanbanCard key={client.id} client={client} />
        ))}

        {/* Empty column placeholder */}
        {clients.length === 0 && (
          <div
            className={cn(
              "rounded-sm border border-dashed border-zx-rule/60 px-3 py-5",
              "font-serif italic text-[13px] text-zx-ink-mute text-center",
              isOver && "border-zx-green/40 text-zx-green"
            )}
            style={{ fontFamily: "Newsreader, serif" }}
          >
            {tEmpty("empty.column")}
          </div>
        )}
      </div>
    </div>
  );
}
