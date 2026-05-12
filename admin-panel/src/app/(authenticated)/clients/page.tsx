"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Building2, Search } from "lucide-react";
import { sileo } from "sileo";
import api from "@/lib/api";
import { formatMonthly } from "@/lib/money";
import type { ClientRead, ClientStage } from "@/lib/types";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { StatusPill } from "@/components/shared/status-pill";
import { FilterChip } from "@/components/shared/filter-chip";
import { Pagination } from "@/components/shared/pagination";

const LIMIT = 25;

const ALL_STAGES: ClientStage[] = [
  "lead",
  "discovery_scheduled",
  "discovery_done",
  "proposal_sent",
  "active",
  "lost",
];

const SECTORS = [
  "Clínicas Dentales",
  "Legal",
  "Logística",
  "Tecnología",
  "Educación",
  "Otros",
];

/** Derive owner initials from owner_id (placeholder until user lookup is available) */
function ownerInitials(ownerId: string | null): string {
  if (!ownerId) return "?";
  return ownerId.slice(0, 2).toUpperCase();
}

export default function ClientsPage() {
  const t = useTranslations("page.clients");
  const tStatus = useTranslations("status");
  const router = useRouter();

  const [clients, setClients] = useState<ClientRead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  // Filters
  const [stage, setStage] = useState<ClientStage | "">("");
  const [ownerId, setOwnerId] = useState<string>("");
  const [sector, setSector] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  // Debounce search 300ms
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setOffset(0);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  const fetchClients = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.getClients({
        limit: LIMIT,
        offset,
        stage: stage || undefined,
        owner_id: ownerId || undefined,
        sector: sector || undefined,
        q: debouncedSearch || undefined,
      });
      setClients(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Error fetching clients:", err);
      const msg = err instanceof Error ? err.message : "Error al cargar los clientes";
      setError(msg);
      sileo.error({ title: t("error.title") ?? "Error al cargar los clientes" });
    } finally {
      setIsLoading(false);
    }
  }, [offset, stage, ownerId, sector, debouncedSearch, t]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  function handleStageChip(s: ClientStage) {
    setStage((prev) => (prev === s ? "" : s));
    setOffset(0);
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        lede={t("lede")}
      />

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-zx-rule px-10 py-4">
        {/* Stage filter chips */}
        <FilterChip active={stage === ""} onClick={() => { setStage(""); setOffset(0); }}>
          {t("filter.allStages")}
        </FilterChip>
        {ALL_STAGES.map((s) => (
          <FilterChip
            key={s}
            active={stage === s}
            onClick={() => handleStageChip(s)}
          >
            {tStatus(s)}
          </FilterChip>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 border-b border-zx-rule px-10 py-3">
        {/* Owner select */}
        <Select value={ownerId || "all"} onValueChange={(v) => { setOwnerId(v === "all" ? "" : v); setOffset(0); }}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={t("filter.allOwners")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filter.allOwners")}</SelectItem>
          </SelectContent>
        </Select>

        {/* Sector select */}
        <Select value={sector || "all"} onValueChange={(v) => { setSector(v === "all" ? "" : v); setOffset(0); }}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder={t("filter.allSectors")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filter.allSectors")}</SelectItem>
            {SECTORS.map((sec) => (
              <SelectItem key={sec} value={sec}>{sec}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zx-ink-mute pointer-events-none" />
          <Input
            className="pl-9"
            placeholder={t("search.placeholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Table */}
      <Card className="mx-10 mt-6 mb-8 border-zx-rule">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          ) : clients.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
              <Building2 className="h-12 w-12 text-zx-ink-mute/40" />
              <div>
                <p className="font-serif text-lg text-zx-ink">{t("empty.title")}</p>
                <p className="text-sm text-zx-ink-mute mt-1">{t("empty.description")}</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("table.name")}</TableHead>
                    <TableHead>{t("table.stage")}</TableHead>
                    <TableHead>{t("table.owner")}</TableHead>
                    <TableHead className="text-right tabular-nums">{t("table.mrr")}</TableHead>
                    <TableHead>{t("table.next_milestone")}</TableHead>
                    <TableHead className="text-right">{t("table.contacts")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((client) => (
                    <TableRow
                      key={client.id}
                      className="cursor-pointer hover:bg-zx-paper-2/60"
                      onClick={() => router.push(`/clients/${client.id}`)}
                    >
                      {/* Name + sector lede */}
                      <TableCell>
                        <div className="font-medium text-zx-ink">{client.name}</div>
                        {client.sector && (
                          <div className="text-[11px] text-zx-ink-mute mt-0.5">
                            {client.sector}
                            {client.region ? ` · ${client.region}` : ""}
                          </div>
                        )}
                      </TableCell>

                      {/* Stage */}
                      <TableCell>
                        <StatusPill status={client.stage} />
                      </TableCell>

                      {/* Owner avatar */}
                      <TableCell>
                        {client.owner_id ? (
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zx-ink text-[11px] font-medium text-zx-paper"
                              aria-hidden="true"
                            >
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

                      {/* MRR */}
                      <TableCell className="text-right tabular-nums text-sm">
                        {formatMonthly(client.mrr_cents)}
                      </TableCell>

                      {/* Next milestone — not in ClientRead, show dash */}
                      <TableCell className="text-sm text-zx-ink-mute">
                        —
                      </TableCell>

                      {/* Contacts count — not in ClientRead, show dash */}
                      <TableCell className="text-right text-sm text-zx-ink-mute">
                        —
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {!isLoading && !error && total > LIMIT && (
            <div className="px-6 py-4 border-t border-zx-rule">
              <Pagination
                total={total}
                limit={LIMIT}
                offset={offset}
                onChange={setOffset}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
