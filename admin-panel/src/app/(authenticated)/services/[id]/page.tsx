"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { format } from "date-fns";
import { ChevronRight, CheckCircle2, Circle } from "lucide-react";
import { sileo } from "sileo";
import api, { ApiError } from "@/lib/api";
import type { ServiceRead, ActivityLogListResponse, MilestoneRead } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusPill } from "@/components/shared/status-pill";
import { ServiceTypeBadge } from "@/components/shared/service-type-badge";
import { ProgressBar } from "@/components/shared/progress-bar";
import { ActivityTimelineItem } from "@/components/shared/activity-timeline-item";
import { ServiceStateTransitionDialog } from "@/components/shared/service-state-transition-dialog";
import { formatMonthly } from "@/lib/money";
import { cn } from "@/lib/utils";

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("page.service_detail");

  const [service, setService] = useState<ServiceRead | null>(null);
  const [activity, setActivity] = useState<ActivityLogListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFoundError, setNotFoundError] = useState(false);
  const [milestoneSaving, setMilestoneSaving] = useState<number | null>(null);

  const fetchService = useCallback(async () => {
    try {
      setIsLoading(true);
      const svc = await api.getService(id);
      setService(svc);
      // Fetch activity filtered by client_id (parallel after we know it)
      const clientActivity = await api
        .getActivity({ client_id: svc.client_id, limit: 20 })
        .catch(() => null);
      setActivity(clientActivity);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFoundError(true);
      } else {
        console.error("Error fetching service:", err);
        sileo.error({
          title: "Error al cargar el servicio",
          description: err instanceof Error ? err.message : "Error desconocido",
        });
      }
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    fetchService();
  }, [fetchService]);

  function handleStateSuccess(updated: ServiceRead) {
    setService((prev) =>
      prev ? { ...prev, state: updated.state, updated_at: updated.updated_at } : prev
    );
  }

  async function handleMilestoneToggle(milestone: MilestoneRead) {
    if (!service) return;
    const newCompletedAt = milestone.completed_at
      ? null
      : new Date().toISOString();

    setMilestoneSaving(milestone.n);
    try {
      const updated = await api.patchMilestone(service.id, milestone.n, {
        completed_at: newCompletedAt,
      });
      setService((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          milestones: prev.milestones.map((m) =>
            m.n === updated.n ? updated : m
          ),
        };
      });
    } catch (err) {
      sileo.error({
        title: "No se pudo actualizar el hito",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    } finally {
      setMilestoneSaving(null);
    }
  }

  if (notFoundError) {
    notFound();
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-10">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-4 w-2/3" />
        <div className="space-y-2 mt-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!service) return null;

  const lede = [
    service.monthly_cents != null ? formatMonthly(service.monthly_cents) : null,
    service.state,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 px-10 py-4 text-[12px] text-zx-ink-mute">
        <Link
          href={`/clients/${service.client_id}`}
          className="hover:text-zx-ink transition-colors"
        >
          {t("breadcrumb")}
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-zx-ink">{service.title}</span>
      </nav>

      {/* Page Header */}
      <PageHeader
        eyebrow={`${t("eyebrow")} · ${service.type}`}
        title={service.title}
        lede={lede || undefined}
        right={
          <div className="flex items-center gap-3">
            <StatusPill status={service.state} />
            <ServiceStateTransitionDialog
              serviceId={service.id}
              currentState={service.state}
              onSuccess={handleStateSuccess}
            />
          </div>
        }
      />

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-0 border-t border-zx-rule">
        {/* Main column */}
        <div className="border-r border-zx-rule">

          {/* Section: Hitos */}
          <section className="border-b border-zx-rule">
            <div className="px-10 py-5 border-b border-zx-rule/50">
              <h2 className="font-serif text-xl text-zx-ink">
                {t("section.milestones")}
              </h2>
            </div>

            {service.milestones.length === 0 ? (
              <div className="px-10 py-10 text-center">
                <p className="font-serif italic text-base text-zx-ink-mute">
                  {t("emptyMilestones")}
                </p>
              </div>
            ) : (
              <ol className="divide-y divide-zx-rule/50">
                {service.milestones.map((milestone) => {
                  const isDone = milestone.completed_at != null;
                  const isSaving = milestoneSaving === milestone.n;

                  return (
                    <li
                      key={milestone.id}
                      className="flex items-center gap-5 px-10 py-4"
                    >
                      {/* Milestone number */}
                      <span
                        className={cn(
                          "font-serif italic text-[28px] leading-none font-light tabular-nums w-12 shrink-0",
                          isDone ? "text-zx-green" : "text-zx-ink/25"
                        )}
                      >
                        {String(milestone.n).padStart(2, "0")}
                      </span>

                      {/* Status circle */}
                      <span className="shrink-0">
                        {isDone ? (
                          <CheckCircle2 className="h-5 w-5 text-zx-green" />
                        ) : (
                          <Circle className="h-5 w-5 text-zx-ink/25" />
                        )}
                      </span>

                      {/* Title */}
                      <div className="flex-1 min-w-0">
                        <span
                          className={cn(
                            "font-serif text-[17px] leading-snug",
                            isDone ? "text-zx-ink" : "text-zx-ink/70"
                          )}
                        >
                          {milestone.title}
                        </span>
                        {milestone.due_date && (
                          <p className="text-[11px] text-zx-ink-mute mt-1">
                            {t("milestone.dueDate")}:{" "}
                            {format(new Date(milestone.due_date), "d MMM yyyy")}
                          </p>
                        )}
                        {isDone && milestone.completed_at && (
                          <p className="text-[11px] text-zx-green mt-0.5">
                            {t("milestone.completed")}:{" "}
                            {format(new Date(milestone.completed_at), "d MMM yyyy")}
                          </p>
                        )}
                      </div>

                      {/* Toggle button */}
                      {!isDone && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isSaving}
                          onClick={() => handleMilestoneToggle(milestone)}
                          className="shrink-0"
                        >
                          {isSaving ? "..." : t("milestone.complete")}
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </section>

          {/* Section: Score (assessment only, score_int not null) */}
          {service.type === "assessment" && service.score_int != null && (
            <section className="border-b border-zx-rule">
              <div className="px-10 py-5 border-b border-zx-rule/50">
                <h2 className="font-serif text-xl text-zx-ink">
                  {t("section.score")}
                </h2>
              </div>
              <div className="px-10 py-8 flex flex-col items-center gap-3">
                <span
                  className="font-serif font-light text-zx-green leading-none"
                  style={{ fontSize: 96, letterSpacing: "-0.04em" }}
                >
                  {service.score_int}
                </span>
                <span className="font-serif italic text-sm text-zx-ink-mute">
                  {t("score.outOf")}
                </span>
              </div>
            </section>
          )}

          {/* Section: Actividad */}
          <section>
            <div className="px-10 py-5 border-b border-zx-rule/50">
              <h2 className="font-serif text-xl text-zx-ink">
                {t("section.activity")}
              </h2>
            </div>

            {!activity || activity.items.length === 0 ? (
              <div className="px-10 py-10 text-center">
                <p className="font-serif italic text-base text-zx-ink-mute">
                  {t("emptyActivity")}
                </p>
              </div>
            ) : (
              <div className="px-10 py-2">
                {activity.items.map((entry) => (
                  <ActivityTimelineItem key={entry.id} entry={entry} />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Sidebar */}
        <aside className="px-8 py-6 space-y-8">
          {/* Section: Cliente */}
          <div>
            <h3 className="text-[10.5px] uppercase tracking-[0.18em] text-zx-ink-mute mb-3">
              {t("section.client")}
            </h3>
            <Link
              href={`/clients/${service.client_id}`}
              className="flex items-center gap-2 text-sm text-zx-green hover:underline"
            >
              <span>{t("viewClient")}</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {/* Progress */}
          {service.progress_pct != null && (
            <div>
              <h3 className="text-[10.5px] uppercase tracking-[0.18em] text-zx-ink-mute mb-3">
                Progreso
              </h3>
              <div className="flex items-center gap-3">
                <ProgressBar value={service.progress_pct} className="flex-1" />
                <span className="text-[11px] text-zx-ink-mute tabular-nums">
                  {service.progress_pct}%
                </span>
              </div>
            </div>
          )}

          {/* Type badge */}
          <div>
            <h3 className="text-[10.5px] uppercase tracking-[0.18em] text-zx-ink-mute mb-3">
              Tipo
            </h3>
            <ServiceTypeBadge type={service.type} />
          </div>

          {/* Owner */}
          {service.owner_id && (
            <div>
              <h3 className="text-[10.5px] uppercase tracking-[0.18em] text-zx-ink-mute mb-3">
                Responsable
              </h3>
              <div className="flex items-center gap-2.5">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zx-ink text-[12px] font-medium text-zx-paper">
                  {service.owner_id.slice(0, 2).toUpperCase()}
                </span>
                <span className="text-xs text-zx-ink-soft font-mono">
                  {service.owner_id.slice(0, 12)}
                </span>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
