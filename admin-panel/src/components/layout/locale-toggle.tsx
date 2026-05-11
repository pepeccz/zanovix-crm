"use client";

import { useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { setLocaleCookie, type Locale } from "@/lib/locale";

const LOCALES: Locale[] = ["es", "en"];

export function LocaleToggle() {
  const active = useLocale() as Locale;
  const router = useRouter();

  function pick(next: Locale) {
    if (next === active) return;
    setLocaleCookie(next);
    router.refresh();
  }

  return (
    <div className="inline-flex overflow-hidden rounded-sm border border-zx-rule text-[11px] uppercase tracking-[0.12em]">
      {LOCALES.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => pick(l)}
          aria-pressed={active === l}
          className={cn(
            "px-2.5 py-1.5 font-semibold transition-colors",
            active === l
              ? "bg-zx-green text-zx-paper"
              : "bg-transparent text-zx-ink-soft hover:bg-zx-paper-2"
          )}
        >
          {l}
        </button>
      ))}
    </div>
  );
}
