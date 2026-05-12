"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Workflow, LayoutList, Kanban } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { sileo } from "sileo";
import api from "@/lib/api";
import { formatMonthly } from "@/lib/money";
import type { ClientRead } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { FilterChip } from "@/components/shared/filter-chip";
import { StatusPill } from "@/components/shared/status-pill";
import { KanbanBoard } from "@/components/kanban/kanban-board";

/** Fetch all pipeline clients without pagination (limit 200 per spec). */
const KANBAN_LIMIT = 200;

const SECTORS = [
  "Clínicas Dentales",
  "Legal",
  "Logística",
  "Tecnología",
  "Educación",
  "Otros",
];

type ViewMode = "kanban" | "list";

/** Owner initials from owner_id (placeholder until /api/users endpoint). */
function ownerInitials(ownerId: string | null): string {
  if (!ownerId) return "?";
  return ownerId.slice(0, 2).toUpperCase();
}

export default function PipelinePage() {
  const t = useTranslations("page.pipeline");
  const tClients = useTranslations("page.clients");
  const tStatus = useTranslations("status");
  const router = useRouter();

  const [clients, setClients] = useState<ClientRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("kanban");

  // Filters (owner + sector — no stage filter on kanban, that IS the columns)
  const [ownerId, setOwnerId] = useState<string>("");
  const [sector, setSector] = useState<string>("");

  // Key to force KanbanBoard remount when filters change (keeps optimistic
  // updates clean by re-initialising board state from fresh data)
  const boardKey = `${ownerId}|${sector}`;

  const fetchClients = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.getClients({
        limit: KANBAN_LIMIT,
        offset: 0,
        owner_id: ownerId || undefined,
        sector: sector || undefined,
      });
      setClients(data.items);
    } catch (err) {
      console.error("Error fetching pipeline clients:", err);
      const msg = err instanceof Error ? err.message : "Error al cargar el pipeline";
      setError(msg);
      sileo.error({ title: "Error al cargar el pipeline" });
    } finally {
      setIsLoading(false);
    }
  }, [ownerId, sector]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  // ─── Skeleton ─────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <PageContainer>
        <PageHeader
          eyebrow={t("eyebrow")}
          title={t("title")}
          lede={t("lede")}
        />
        <div className="p-10">
          <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-12 w-full" />
                {Array.from({ length: 3 }).map((_, j) => (
                  <Skeleton key={j} className="h-20 w-full" />
                ))}
              </div>
            ))}
          </div>
        </div>
      </PageContainer>
    );
  }

  // ─── Error ────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <PageContainer>
        <PageHeader
          eyebrow={t("eyebrow")}
          title={t("title")}
          lede={t("lede")}
        />
        <div className="flex flex-col items-center justify-center py-24">
          <p className="text-sm text-red-600">{error}</p>
          <Button variant="outline" onClick={fetchClients} className="mt-4">
            Reintentar
          </Button>
        </div>
      </PageContainer>
    );
  }

  // ─── Main render ──────────────────────────────────────────────────────────

  return (
    <PageContainer>
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        lede={t("lede")}
        right={
          /* View toggle */
          <div className="inline-flex border border-zx-rule rounded-sm overflow-hidden">
            <button
              type="button"
              onClick={() => setView("kanban")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 font-sans text-[12px] transition-colors",
                view === "kanban"
                  ? "bg-zx-ink text-zx-paper"
                  : "text-zx-ink-soft hover:text-zx-ink hover:bg-zx-paper-2"
              )}
            >
              <Kanban className="h-3.5 w-3.5" />
              {t("view.kanban")}
            </button>
            <button
              type="button"
              onClick={() => setView("list")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 font-sans text-[12px] transition-colors border-l border-zx-rule",
                view === "list"
                  ? "bg-zx-ink text-zx-paper"
                  : "text-zx-ink-soft hover:text-zx-ink hover:bg-zx-paper-2"
              )}
            >
              <LayoutList className="h-3.5 w-3.5" />
              {t("view.list")}
            </button>
          </div>
        }
      />

      {/* Filter bar (owner + sector — preserved across view toggle) */}
      <div className="flex flex-wrap items-center gap-3 border-b border-zx-rule px-10 py-3">
        <Select
          value={ownerId || "all"}
          onValueChange={(v) => setOwnerId(v === "all" ? "" : v)}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={tClients("filter.allOwners")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{tClients("filter.allOwners")}</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={sector || "all"}
          onValueChange={(v) => setSector(v === "all" ? "" : v)}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={tClients("filter.allSectors")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{tClients("filter.allSectors")}</SelectItem>
            {SECTORS.map((sec) => (
              <SelectItem key={sec} value={sec}>
                {sec}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Drag hint (kanban view only) */}
        {view === "kanban" && (
          <span
            className="ml-2 font-serif italic text-[13px] text-zx-ink-mute"
            style={{ fontFamily: "Newsreader, serif" }}
          >
            {t("drag_hint")}
          </span>
        )}
      </div>

      {/* Content: Kanban board or List */}
      {view === "kanban" ? (
        <KanbanBoard key={boardKey} clients={clients} />
      ) : (
        <PipelineListView clients={clients} router={router} tClients={tClients} tStatus={tStatus} />
      )}
    </PageContainer>
  );
}

// ─── List view (mirrors /clients table style) ────────────────────────────────

interface PipelineListViewProps {
  clients: ClientRead[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  router: any;
  tClients: (key: string) => string;
  tStatus: (key: string) => string;
}

function PipelineListView({ clients, router, tClients, tStatus }: PipelineListViewProps) {
  // Exclude "lost" from list — pipeline view focuses on active stages
  const pipelineClients = clients.filter((c) => c.stage !== "lost");

  if (pipelineClients.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
        <Workflow className="h-10 w-10 text-zx-ink-mute/40" />
        <p className="font-serif text-lg text-zx-ink">{tClients("empty.title")}</p>
        <p className="text-sm text-zx-ink-mute">{tClients("empty.description")}</p>
      </div>
    );
  }

  return (
    <Card className="mx-10 mt-6 mb-8 border-zx-rule">
      <CardContent className="p-0 overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{tClients("table.name")}</TableHead>
              <TableHead>{tClients("table.stage")}</TableHead>
              <TableHead>{tClients("table.owner")}</TableHead>
              <TableHead className="text-right tabular-nums">{tClients("table.mrr")}</TableHead>
              <TableHead>{tClients("table.next_milestone")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pipelineClients.map((client) => (
              <TableRow
                key={client.id}
                className="cursor-pointer hover:bg-zx-paper-2/60"
                onClick={() => router.push(`/clients/${client.id}`)}
              >
                <TableCell>
                  <div className="font-medium text-zx-ink">{client.name}</div>
                  {client.sector && (
                    <div className="text-[11px] text-zx-ink-mute mt-0.5">
                      {client.sector}
                      {client.region ? ` · ${client.region}` : ""}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <StatusPill status={client.stage} />
                </TableCell>
                <TableCell>
                  {client.owner_id ? (
                    <div className="flex items-center gap-2">
                      <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zx-ink text-[11px] font-medium text-zx-paper">
                        {ownerInitials(client.owner_id)}
                      </span>
                      <span className="text-xs text-zx-ink-soft font-mono">
                        {client.owner_id.slice(0, 8)}
                      </span>
                    </div>
                  ) : (
                    <span className="text-zx-ink-mute text-sm italic">—</span>
                  )}
                </TableCell>
                <TableCell className="text-right tabular-nums text-sm">
                  {formatMonthly(client.mrr_cents)}
                </TableCell>
                <TableCell className="text-sm text-zx-ink-mute">—</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
