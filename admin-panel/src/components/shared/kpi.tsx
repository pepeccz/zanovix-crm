"use client";

import { cn } from "@/lib/utils";

/**
 * KPI — editorial KPI card with Newsreader serif value.
 *
 * - label: Inter uppercase micro label
 * - value: Newsreader 32–48px tabular-nums (no fill, hairline right border)
 * - delta: optional italic delta (green if positive, terra if negative)
 * - footnote: optional italic italic footnote below the value
 */

interface KPIProps {
  label: string;
  value: string;
  delta?: string;
  footnote?: string;
  className?: string;
}

function isDeltaNegative(delta: string): boolean {
  return delta.startsWith("−") || delta.startsWith("-");
}

export function KPI({ label, value, delta, footnote, className }: KPIProps) {
  return (
    <div
      className={cn(
        "border-r border-zx-rule px-6 py-5 last:border-r-0",
        className
      )}
    >
      {/* Label */}
      <p className="mb-3 font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zx-ink-mute">
        {label}
      </p>

      {/* Value row */}
      <div className="flex items-baseline gap-3">
        <span
          className={cn(
            "font-serif font-normal leading-none tracking-[-0.02em] text-zx-ink",
            "text-[38px] tabular-nums"
          )}
        >
          {value}
        </span>

        {delta && (
          <span
            className={cn(
              "font-serif italic text-sm leading-none",
              isDeltaNegative(delta) ? "text-zx-terra" : "text-zx-green"
            )}
          >
            {delta}
          </span>
        )}
      </div>

      {/* Footnote */}
      {footnote && (
        <p className="mt-2 font-serif italic text-[13px] leading-snug text-zx-ink-mute">
          {footnote}
        </p>
      )}
    </div>
  );
}
