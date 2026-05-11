"use client";

import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid h-screen grid-cols-[232px_1fr] grid-rows-[auto_1fr] overflow-hidden">
      <Sidebar className="row-span-2 overflow-y-auto" />
      <Topbar />
      <main className="overflow-y-auto bg-zx-paper p-10">{children}</main>
    </div>
  );
}
