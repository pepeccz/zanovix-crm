"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/**
 * StatusPill — Outline pill for CRM stage/state values.
 *
 * Color mapping (zx-* tokens only):
 *   green  → active, paid, completed, go, running, delivered, won
 *   terra  → pending, development, proposal_sent, discovery_scheduled, discovery_done, scheduled, review
 *   red    → overdue, lost
 *   muted  → lead, draft, scoping, in_progress, maintenance, paused
 *
 * Label is resolved via `useTranslations("status")` with key = status value.
 */

type StatusColor = "green" | "terra" | "red" | "muted";

const COLOR_MAP: Record<string, StatusColor> = {
  // green group
  active: "green",
  paid: "green",
  completed: "green",
  go: "green",
  running: "green",
  delivered: "green",
  won: "green",
  in_progress: "green",
  // terra group
  pending: "terra",
  development: "terra",
  proposal_sent: "terra",
  discovery_scheduled: "terra",
  discovery_done: "terra",
  scheduled: "terra",
  review: "terra",
  maintenance: "terra",
  // red group
  overdue: "red",
  lost: "red",
  // muted group (default)
  lead: "muted",
  draft: "muted",
  scoping: "muted",
  paused: "muted",
};

const COLOR_CLASSES: Record<StatusColor, { pill: string; dot: string }> = {
  green: {
    pill: "border-zx-green text-zx-green-dark",
    dot: "bg-zx-green",
  },
  terra: {
    pill: "border-zx-terra text-zx-terra",
    dot: "bg-zx-terra",
  },
  red: {
    pill: "border-red-600 text-red-600",
    dot: "bg-red-600",
  },
  muted: {
    pill: "border-zx-ink-soft text-zx-ink-mute",
    dot: "bg-zx-ink-soft",
  },
};

interface StatusPillProps {
  status: string;
  className?: string;
}

export function StatusPill({ status, className }: StatusPillProps) {
  const t = useTranslations("status");
  const color = COLOR_MAP[status] ?? "muted";
  const { pill, dot } = COLOR_CLASSES[color];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5",
        "font-sans text-[11px] font-medium uppercase tracking-[0.04em] whitespace-nowrap",
        pill,
        className
      )}
    >
      <span className={cn("inline-block h-1.5 w-1.5 rounded-full shrink-0", dot)} />
      {t(status)}
    </span>
  );
}
