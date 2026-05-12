"use client";

import type { ReactNode } from "react";
import { ClientSidebar } from "./client-sidebar";
import { ClientTopbar } from "./client-topbar";

export function ClientAppShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid h-screen grid-cols-[232px_1fr] grid-rows-[auto_1fr] overflow-hidden">
      <ClientSidebar className="row-span-2 overflow-y-auto" />
      <ClientTopbar />
      <main className="overflow-y-auto bg-zx-paper p-10">{children}</main>
    </div>
  );
}
