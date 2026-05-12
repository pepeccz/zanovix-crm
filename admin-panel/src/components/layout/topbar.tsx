"use client";

import { useTranslations } from "next-intl";
import { LogOut, ChevronDown } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { LocaleToggle } from "./locale-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export function Topbar() {
  const t = useTranslations();
  const { user, logout } = useAuth();

  const displayName = user?.display_name ?? user?.email ?? "";
  const initials = getInitials(displayName);

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-end gap-3 border-b border-zx-rule bg-zx-paper px-10">
      <span className="font-serif italic text-sm text-zx-ink-mute">
        {t("shell.view_internal")}
      </span>
      <LocaleToggle />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label={displayName || "user"}
            title={displayName}
            className="group flex items-center gap-2 rounded-[2px] border border-zx-rule bg-zx-paper px-2 py-1 outline-none transition-colors hover:bg-zx-paper-2 focus:ring-2 focus:ring-zx-ink/30"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-zx-ink text-[11px] font-semibold text-zx-paper">
              {initials || "?"}
            </span>
            {displayName ? (
              <span className="hidden font-sans text-[12px] text-zx-ink-soft md:inline-block max-w-[10rem] truncate">
                {displayName.split(" ")[0]}
              </span>
            ) : null}
            <ChevronDown className="h-3.5 w-3.5 text-zx-ink-mute transition-transform group-data-[state=open]:rotate-180" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[12rem]">
          {displayName ? (
            <DropdownMenuLabel className="truncate">
              {displayName}
            </DropdownMenuLabel>
          ) : null}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => logout()}>
            <LogOut className="h-4 w-4" />
            {t("topbar.userMenu.signOut")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
