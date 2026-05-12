"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * FilterChip — Pill toggle for filter selections.
 *
 * Active state:  bg-zx-ink, text-zx-paper, border-zx-ink
 * Inactive state: transparent bg, text-zx-ink-soft, border-zx-rule
 *
 * Props:
 *   active    — whether this chip is currently selected
 *   count?    — optional numeric badge shown after the label (tabular-nums)
 *   onClick   — toggle handler
 *   children  — label content
 */

interface FilterChipProps {
  active: boolean;
  count?: number;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}

export function FilterChip({
  active,
  count,
  onClick,
  children,
  className,
}: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1",
        "font-sans text-xs font-medium transition-all duration-150 cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zx-green focus-visible:ring-offset-1",
        active
          ? "border-zx-ink bg-zx-ink text-zx-paper"
          : "border-zx-rule bg-transparent text-zx-ink-soft hover:border-zx-ink-soft",
        className
      )}
    >
      {children}
      {count != null && (
        <span className="tabular-nums text-[11px] opacity-70">{count}</span>
      )}
    </button>
  );
}
