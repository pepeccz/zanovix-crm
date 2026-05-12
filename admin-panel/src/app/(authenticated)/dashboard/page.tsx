"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import api from "@/lib/api";
import { formatMonthly } from "@/lib/money";
import type {
  ClientRead,
  ServiceListResponse,
  ActivityLogListResponse,
  ClientStage,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { KPI } from "@/components/shared/kpi";
import { ProgressBar } from "@/components/shared/progress-bar";
import { ActivityTimelineItem } from "@/components/shared/activity-timeline-item";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Stages included in the pipeline funnel (excludes "lost"). */
const PIPELINE_STAGES: ClientStage[] = [
  "lead",
  "discovery_scheduled",
  "discovery_done",
  "proposal_sent",
  "active",
];

/** Stages that count as "deals in motion". */
const DEALS_IN_MOTION_STAGES: ClientStage[] = [
  "discovery_scheduled",
  "discovery_done",
  "proposal_sent",
];

/** Service states that count toward pipeline value. */
const PIPELINE_SERVICE_STATES = new Set(["scoping", "running"]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function todayLede(): string {
  return new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function DashboardSkeleton() {
  return (
    <div className="animate-pulse">
      {/* KPI row */}
      <div className="grid grid-cols-4 border-b border-zx-rule">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border-r border-zx-rule px-6 py-5 last:border-r-0">
            <Skeleton className="h-3 w-24 mb-4" />
            <Skeleton className="h-10 w-32" />
          </div>
        ))}
      </div>

      {/* Body sections */}
      <div className="grid grid-cols-[1.4fr_1fr] divide-x divide-zx-rule border-b border-zx-rule">
        {/* Funnel skeleton */}
        <div className="px-10 py-6 space-y-4">
          <Skeleton className="h-3 w-32 mb-6" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="space-y-1.5">
              <div className="flex justify-between">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-3 w-12" />
              </div>
              <Skeleton className="h-[5px] w-full" />
            </div>
          ))}
        </div>

        {/* Activity skeleton */}
        <div className="px-10 py-6 space-y-4">
          <Skeleton className="h-3 w-32 mb-6" />
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-5 w-5 rounded-full shrink-0" />
              <div className="space-y-1 flex-1">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-2.5 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const t = useTranslations("page.dashboard");
  const tStage = useTranslations("stage");

  // Data state
  const [clients, setClients] = useState<ClientRead[]>([]);
  const [clientsTotal, setClientsTotal] = useState(0);
  const [services, setServices] = useState<ServiceListResponse | null>(null);
  const [activity, setActivity] = useState<ActivityLogListResponse | null>(null);

  // Loading / error state split so activity can degrade independently
  const [isLoading, setIsLoading] = useState(true);
  const [clientsError, setClientsError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setClientsError(null);
    setActivityError(null);

    // Parallel fetch of all three sources
    const [clientsResult, servicesResult, activityResult] = await Promise.allSettled([
      api.getClients({ limit: 200 }),
      api.getServices({ limit: 200 }),
      api.getActivity({ limit: 30 }),
    ]);

    // Clients + services — if either fails, KPIs and funnel are degraded
    if (clientsResult.status === "fulfilled") {
      const data = clientsResult.value;
      setClients(data.items);
      setClientsTotal(data.total);

      // ADR-D5 tripwire: when total > items, KPI accuracy is capped
      if (data.total > data.items.length) {
        console.warn(
          `[Dashboard] KPI accuracy capped: total clients=${data.total} but only ${data.items.length} loaded (limit 200). Add GET /api/dashboard/kpis for accurate aggregation.`
        );
      }
    } else {
      const err = clientsResult.reason;
      setClientsError(err instanceof Error ? err.message : "Error al cargar datos");
    }

    if (servicesResult.status === "fulfilled") {
      setServices(servicesResult.value);
    } else if (clientsResult.status === "fulfilled") {
      // Clients loaded fine but services failed — KPI pipeline value will be degraded
      setClientsError("Error al cargar servicios");
    }
    // If clientsResult already failed, clientsError is already set above

    // Activity error degrades only the feed section
    if (activityResult.status === "fulfilled") {
      setActivity(activityResult.value);
    } else {
      const err = activityResult.reason;
      setActivityError(err instanceof Error ? err.message : "Error al cargar actividad");
    }

    setIsLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ---------------------------------------------------------------------------
  // KPI calculations (memoised)
  // ---------------------------------------------------------------------------

  const mrr = useMemo(() => {
    if (clientsError) return null;
    return clients
      .filter((c) => c.stage === "active")
      .reduce((sum, c) => sum + (c.mrr_cents ?? 0), 0);
  }, [clients, clientsError]);

  const pipelineValue = useMemo(() => {
    if (!services || clientsError) return null;
    return services.items
      .filter((s) => PIPELINE_SERVICE_STATES.has(s.state))
      .reduce((sum, s) => sum + (s.setup_price_cents ?? 0), 0);
  }, [services, clientsError]);

  const dealsInMotion = useMemo(() => {
    if (clientsError) return null;
    return clients.filter((c) => DEALS_IN_MOTION_STAGES.includes(c.stage)).length;
  }, [clients, clientsError]);

  // ---------------------------------------------------------------------------
  // Funnel data (memoised)
  // ---------------------------------------------------------------------------

  const funnelRows = useMemo(() => {
    const counts = PIPELINE_STAGES.map((stage) => ({
      stage,
      count: clients.filter((c) => c.stage === stage).length,
    }));
    const max = Math.max(...counts.map((r) => r.count), 1);
    return counts.map((r) => ({
      ...r,
      pct: Math.round((r.count / max) * 100),
    }));
  }, [clients]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isLoading) return <DashboardSkeleton />;

  const isDegraded = !!clientsError;

  return (
    <div>
      {/* Page header */}
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        lede={todayLede()}
      />

      {/* KPI row — 4 columns with hairline borders */}
      <div className="grid grid-cols-2 border-b border-zx-rule md:grid-cols-4">
        <KPI
          label={t("kpi.mrr")}
          value={isDegraded ? "—" : formatMonthly(mrr)}
        />
        <KPI
          label={t("kpi.pipelineValue")}
          value={isDegraded ? "—" : formatMonthly(pipelineValue)}
        />
        <KPI
          label={t("kpi.dealsInMotion")}
          value={isDegraded ? "—" : String(dealsInMotion ?? 0)}
        />
        <KPI
          label={t("kpi.nextBilling")}
          value="—"
          footnote={t("kpi.nextBillingFootnote")}
        />
      </div>

      {/* Degraded state banner */}
      {isDegraded && (
        <div className="flex items-center gap-2 border-b border-zx-rule bg-zx-paper-2 px-10 py-3 text-[13px] text-zx-terra">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{t("error.degraded")}</span>
        </div>
      )}

      {/* Two-column body: funnel (left) + activity feed (right) */}
      <div className="grid grid-cols-1 border-b border-zx-rule lg:grid-cols-[1.4fr_1fr] lg:divide-x lg:divide-zx-rule">

        {/* Pipeline funnel */}
        <div className="border-b border-zx-rule px-10 py-8 lg:border-b-0">
          <p className="mb-6 font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zx-ink-mute">
            {t("section.funnel")}
          </p>

          {isDegraded ? (
            <p className="font-serif italic text-sm text-zx-ink-mute">{t("funnel.empty")}</p>
          ) : (
            <div className="space-y-4">
              {funnelRows.map(({ stage, count, pct }) => (
                <div key={stage}>
                  <div className="mb-1.5 flex items-baseline justify-between gap-4">
                    <span className="font-sans text-[12px] text-zx-ink-soft">
                      {tStage(stage)}
                    </span>
                    <span className="font-sans text-[12px] tabular-nums text-zx-ink-mute">
                      {count}
                    </span>
                  </div>
                  <ProgressBar
                    value={pct}
                    color={
                      stage === "active"
                        ? "bg-zx-green"
                        : stage === "lost"
                        ? "bg-zx-ink-mute"
                        : "bg-zx-ink"
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Activity feed */}
        <div className="px-10 py-8">
          <p className="mb-4 font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zx-ink-mute">
            {t("section.activity")}
          </p>

          {activityError ? (
            <div className="flex items-start gap-2 rounded border border-zx-rule bg-zx-paper-2 p-4">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-zx-terra" />
              <div>
                <p className="text-[13px] font-medium text-zx-ink-soft">{t("error.activityFeed")}</p>
                <p className="mt-0.5 text-[12px] text-zx-ink-mute">{activityError}</p>
              </div>
            </div>
          ) : !activity || activity.items.length === 0 ? (
            <p className="font-serif italic text-sm text-zx-ink-mute">{t("activity.empty")}</p>
          ) : (
            <div>
              {activity.items.map((entry) => (
                <ActivityTimelineItem key={entry.id} entry={entry} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
