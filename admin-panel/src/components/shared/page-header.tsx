"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PageHeader — Editorial serif page header per Zanovix CRM design handoff.
 *
 * Props:
 *   eyebrow?  — Newsreader italic, terra color, prefixed with "—"
 *   title     — Newsreader 38px, zx-ink, balance wrap
 *   lede?     — Newsreader italic, muted, max 60ch
 *   right?    — Actions slot (buttons, badges, etc.) aligned to bottom-right
 *   className?
 *
 * For non-CRM pages that used the old API (title + description + actions),
 * use the `description` and `actions` aliases below — they forward transparently.
 */

interface PageHeaderProps {
  /** Optional editorial eyebrow (italic, terra, prefixed with em dash) */
  eyebrow?: string;
  /** Primary serif headline — required */
  title: string;
  /** Optional italic lede below the title (max 60ch) */
  lede?: string;
  /** Optional slot for action buttons or status badges (right-aligned) */
  right?: React.ReactNode;
  /** @deprecated Use `lede` instead */
  description?: string;
  /** @deprecated Use `right` instead */
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  lede,
  right,
  description,
  actions,
  className,
}: PageHeaderProps) {
  const ledeText = lede ?? description;
  const rightSlot = right ?? actions;

  return (
    <header
      className={cn(
        "flex items-end justify-between gap-8 border-b border-zx-rule px-10 pb-7 pt-8",
        className
      )}
    >
      {/* Left: eyebrow + title + lede */}
      <div className="max-w-2xl min-w-0">
        {eyebrow && (
          <p className="mb-2.5 font-serif italic text-sm text-zx-green leading-none">
            — {eyebrow}
          </p>
        )}

        <h1
          className={cn(
            "font-serif font-normal tracking-[-0.02em] text-zx-ink",
            "text-[38px] leading-[1.1] text-balance m-0"
          )}
        >
          {title}
        </h1>

        {ledeText && (
          <p className="mt-3 max-w-[60ch] font-serif italic text-base leading-relaxed text-zx-ink-mute">
            {ledeText}
          </p>
        )}
      </div>

      {/* Right: actions slot */}
      {rightSlot && (
        <div className="flex shrink-0 items-center gap-2.5">{rightSlot}</div>
      )}
    </header>
  );
}
