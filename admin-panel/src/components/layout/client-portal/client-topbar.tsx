"use client";

import { useAuth } from "@/contexts/auth-context";
import { LocaleToggle } from "../locale-toggle";

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export function ClientTopbar() {
  const { user } = useAuth();

  const displayName = user?.display_name ?? user?.email ?? "";
  const initials = getInitials(displayName);

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-end gap-3 border-b border-zx-rule bg-zx-paper px-10">
      <LocaleToggle />
      <div
        aria-label={displayName || "user"}
        title={displayName}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-zx-green text-xs font-semibold text-zx-paper"
      >
        {initials || "?"}
      </div>
    </header>
  );
}
