"use client";

import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Pagination — CRM-aware pagination with i18n labels.
 *
 * Resolves `pagination.{showing,prev,next,of}` via next-intl.
 *
 * Props:
 *   total     — total record count
 *   limit     — page size
 *   offset    — current offset (0-based)
 *   onChange  — callback receives new offset
 */

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  className?: string;
}

export function Pagination({
  total,
  limit,
  offset,
  onChange,
  className,
}: PaginationProps) {
  const t = useTranslations("pagination");

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  const isPrevDisabled = offset === 0;
  const isNextDisabled = offset + limit >= total;

  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      {/* "Showing X–Y of Z" */}
      <p className="min-w-0 truncate text-sm text-zx-ink-mute">
        {t("showing")}{" "}
        <span className="font-medium text-zx-ink">
          {from}–{to}
        </span>{" "}
        {t("of")}{" "}
        <span className="font-medium text-zx-ink">{total}</span>
      </p>

      {/* Prev / Next buttons */}
      <div className="flex shrink-0 items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={isPrevDisabled}
          aria-label={t("prev")}
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="hidden sm:inline">{t("prev")}</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(offset + limit)}
          disabled={isNextDisabled}
          aria-label={t("next")}
        >
          <span className="hidden sm:inline">{t("next")}</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
