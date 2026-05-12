"use client";

import { useDraggable } from "@dnd-kit/core";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { formatMonthly } from "@/lib/money";
import type { ClientRead } from "@/lib/types";

interface KanbanCardProps {
  client: ClientRead;
}

/**
 * KanbanCard — individual draggable card inside a kanban column.
 *
 * useDraggable id = client.id (string UUID).
 * Clicking the card navigates to /clients/[id].
 * Owner is shown as initials avatar (first 2 chars of owner_id since no
 * /api/users endpoint exists yet — known limitation from PR 5).
 *
 * Design §3: zx-paper background, hover lift, Newsreader 15px name,
 * Inter 11px sector chip, MRR if any, owner initials.
 */
export function KanbanCard({ client }: KanbanCardProps) {
  const router = useRouter();
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: client.id });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: 999,
      }
    : undefined;

  // Owner initials: first 2 chars of UUID (placeholder until /api/users)
  const ownerInitials = client.owner_id
    ? client.owner_id.slice(0, 2).toUpperCase()
    : "—";

  function handleClick(e: React.MouseEvent) {
    // Prevent navigation when dragging
    if (isDragging) return;
    e.stopPropagation();
    router.push(`/clients/${client.id}`);
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={handleClick}
      className={cn(
        "group relative rounded-sm border bg-zx-paper px-3 py-3 cursor-grab",
        "border-zx-rule transition-all duration-150",
        "hover:border-zx-green/40 hover:-translate-y-px hover:shadow-sm",
        isDragging && "opacity-50 cursor-grabbing shadow-md"
      )}
    >
      {/* Client name */}
      <p
        className="font-serif text-[15px] font-medium leading-snug text-zx-ink mb-1"
        style={{ fontFamily: "Newsreader, serif" }}
      >
        {client.name}
      </p>

      {/* Sector chip */}
      {client.sector && (
        <p className="font-sans text-[11px] text-zx-ink-soft mb-2.5 tracking-[0.01em]">
          {client.sector}
          {client.size ? ` · ${client.size}` : ""}
        </p>
      )}

      {/* Footer: owner avatar + MRR */}
      <div className="flex items-center justify-between">
        {/* Owner avatar */}
        <span
          className={cn(
            "inline-flex items-center justify-center h-5 w-5 rounded-full text-[9px] font-sans font-semibold shrink-0",
            client.owner_id
              ? "bg-zx-ink text-zx-paper"
              : "bg-zx-paper-2 text-zx-ink-mute border border-zx-rule"
          )}
        >
          {ownerInitials}
        </span>

        {/* MRR */}
        {client.mrr_cents != null && (
          <span className="font-sans text-[11.5px] tabular-nums text-zx-ink">
            {formatMonthly(client.mrr_cents)}
          </span>
        )}
      </div>
    </div>
  );
}
