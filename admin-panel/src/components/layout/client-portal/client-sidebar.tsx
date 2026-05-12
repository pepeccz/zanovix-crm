"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { BrandBlock } from "../brand-block";
import { CLIENT_NAV_ITEMS } from "./client-nav-items";

export function ClientSidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const t = useTranslations();

  const isActive = (href: string) => {
    // Exact match for dashboard root to avoid /client matching /client/diagnostic
    if (href === "/client") return pathname === "/client";
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <aside
      className={cn(
        "flex w-[232px] flex-col border-r border-zx-rule bg-zx-paper",
        className
      )}
    >
      <BrandBlock />
      <nav className="flex-1 overflow-y-auto py-4">
        {CLIENT_NAV_ITEMS.map((item) => {
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
      </nav>
      <div className="border-t border-zx-rule px-5 py-4">
        <p className="text-[11px] text-zx-ink-mute tracking-wide">
          {t("shell.view_client")}
        </p>
      </div>
    </aside>
  );
}
