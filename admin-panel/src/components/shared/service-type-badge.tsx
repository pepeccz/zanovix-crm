"use client";

import { useTranslations } from "next-intl";
import { Stethoscope, Code2, GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ServiceType } from "@/lib/types";

/**
 * ServiceTypeBadge — Icon + i18n label pill on bg-zx-paper-2.
 *
 * Icons:
 *   assessment  → Stethoscope
 *   development → Code2
 *   formation   → GraduationCap
 *
 * Label resolved via `useTranslations("serviceType")`.
 */

const TYPE_CONFIG: Record<
  ServiceType,
  { icon: React.ComponentType<{ className?: string }>; colorClass: string }
> = {
  assessment: {
    icon: Stethoscope,
    colorClass: "text-zx-green-dark",
  },
  development: {
    icon: Code2,
    colorClass: "text-zx-ink",
  },
  formation: {
    icon: GraduationCap,
    colorClass: "text-zx-terra",
  },
};

interface ServiceTypeBadgeProps {
  type: ServiceType;
  className?: string;
}

export function ServiceTypeBadge({ type, className }: ServiceTypeBadgeProps) {
  const t = useTranslations("serviceType");
  const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.assessment;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm bg-zx-paper-2 px-2 py-1",
        "font-sans text-[11px] font-medium tracking-[0.02em] whitespace-nowrap",
        config.colorClass,
        className
      )}
    >
      <Icon className="h-3 w-3 shrink-0" />
      {t(type)}
    </span>
  );
}
