"use client";

import { cn } from "@/lib/utils";

/**
 * ProgressBar — 5px tall horizontal progress bar.
 *
 * Track:  bg-zx-paper-2
 * Fill:   bg-zx-green (default) or custom color class via `color`
 * Role:   progressbar (accessible)
 */

interface ProgressBarProps {
  /** 0–100 percentage value */
  value: number;
  /** Optional Tailwind bg-* class for the fill. Defaults to bg-zx-green. */
  color?: string;
  className?: string;
}

export function ProgressBar({ value, color, className }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("h-[5px] w-full overflow-hidden rounded-full bg-zx-paper-2", className)}
    >
      <div
        className={cn("h-full rounded-full", color ?? "bg-zx-green")}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
