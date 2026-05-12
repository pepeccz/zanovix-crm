"use client";

import { useTranslations } from "next-intl";
import {
  ArrowRightLeft,
  UserPlus,
  UserPen,
  PlayCircle,
  RefreshCw,
  CheckCircle2,
  TrendingUp,
  StickyNote,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ActivityLogRead, ActivityKind } from "@/lib/types";

/**
 * ActivityTimelineItem — Single timeline entry.
 *
 * Left: vertical zx-rule line + kind icon
 * Body: i18n description from `activity.{kind}` + relative timestamp
 */

type IconComponent = React.ComponentType<{ className?: string }>;

const KIND_ICONS: Record<ActivityKind, IconComponent> = {
  stage_change: ArrowRightLeft,
  contact_added: UserPlus,
  contact_updated: UserPen,
  service_started: PlayCircle,
  service_state_change: RefreshCw,
  milestone_completed: CheckCircle2,
  lead_converted: TrendingUp,
  note: StickyNote,
};

function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMin < 1) return "ahora";
    if (diffMin < 60) return `hace ${diffMin}m`;
    if (diffHours < 24) return `hace ${diffHours}h`;
    if (diffDays < 7) return `hace ${diffDays}d`;

    return date.toLocaleDateString("es-ES", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return isoString;
  }
}

interface ActivityTimelineItemProps {
  entry: ActivityLogRead;
  className?: string;
}

export function ActivityTimelineItem({
  entry,
  className,
}: ActivityTimelineItemProps) {
  const t = useTranslations("activity");
  const Icon = KIND_ICONS[entry.kind] ?? Activity;

  return (
    <div className={cn("relative flex gap-3 py-3", className)}>
      {/* Left rule + icon */}
      <div className="relative flex flex-col items-center">
        {/* Vertical connecting line */}
        <div className="absolute top-5 bottom-0 left-[50%] w-px -translate-x-1/2 bg-zx-rule" />
        {/* Icon circle */}
        <span className="relative z-10 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-zx-paper-2 ring-1 ring-zx-rule">
          <Icon className="h-2.5 w-2.5 text-zx-ink-soft" />
        </span>
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0 pb-1">
        <p className="text-[13px] leading-snug text-zx-ink-soft">
          {t(entry.kind)}
          {entry.body ? (
            <span className="ml-1 text-zx-ink-mute">— {entry.body}</span>
          ) : null}
        </p>
        <p className="mt-0.5 font-sans text-[11px] text-zx-ink-mute">
          {formatRelativeTime(entry.created_at)}
        </p>
      </div>
    </div>
  );
}
