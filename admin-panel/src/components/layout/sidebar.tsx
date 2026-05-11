"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { BrandBlock } from "./brand-block";
import { NAV_ITEMS, type NavGroup } from "./nav-items";

const GROUP_ORDER: NavGroup[] = ["trabajo", "personas", "recurrentes"];

const GROUP_LABEL_KEYS: Record<NavGroup, string> = {
  trabajo: "sidebar.trabajo",
  personas: "sidebar.personas",
  recurrentes: "sidebar.recurrentes",
};

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const t = useTranslations();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const itemsByGroup = GROUP_ORDER.reduce<Record<NavGroup, typeof NAV_ITEMS>>(
    (acc, group) => {
      acc[group] = NAV_ITEMS.filter((item) => item.group === group);
      return acc;
    },
    { trabajo: [], personas: [], recurrentes: [] }
  );

  return (
    <aside
      className={cn(
        "flex w-[232px] flex-col border-r border-zx-rule bg-zx-paper",
        className
      )}
    >
      <BrandBlock />
      <nav className="flex-1 overflow-y-auto py-4">
        {GROUP_ORDER.map((group) => {
          const items = itemsByGroup[group];
          if (items.length === 0) return null;
          return (
            <div key={group} className="mb-4">
              <p className="mb-1 px-5 text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute">
                {t(GROUP_LABEL_KEYS[group])}
              </p>
              {items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "mb-0.5 flex items-center gap-3 border-l-2 py-2 px-5 text-[13px] transition-colors",
                      active
                        ? "border-zx-green bg-zx-green/10 font-semibold text-zx-ink"
                        : "border-transparent text-zx-ink-soft hover:bg-zx-paper-2"
                    )}
                  >
                    <Icon className="h-[15px] w-[15px] shrink-0" />
                    {t(item.key)}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>
      <div className="border-t border-zx-rule px-5 py-4 space-y-1.5">
        <p className="text-[11px] text-zx-ink-mute tracking-wide">
          {t("google.synced")}
        </p>
        <p className="text-[11px] text-zx-ink-mute tracking-wide">
          {t("stripe.synced")}
        </p>
      </div>
    </aside>
  );
}
