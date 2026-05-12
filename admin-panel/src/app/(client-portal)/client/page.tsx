"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import api from "@/lib/api";
import type { ClientRead, ServiceRead, ActivityLogRead } from "@/lib/types";
import { cn } from "@/lib/utils";
import { sileo } from "sileo";

function KPICard({
  label,
  value,
  footnote,
}: {
  label: string;
  value: string | number;
  footnote?: string;
}) {
  return (
    <div className="border-b border-zx-rule p-6">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute">
        {label}
      </p>
      <p className="mt-2 font-serif text-4xl text-zx-ink">{value}</p>
      {footnote && (
        <p className="mt-1 font-serif italic text-[13px] text-zx-ink-mute">
          {footnote}
        </p>
      )}
    </div>
  );
}

function ServiceCard({ service }: { service: ServiceRead }) {
  const t = useTranslations();
  const progress = service.progress_pct ?? 0;

  const typeLabel: Record<string, string> = {
    assessment: t("svc.assessment"),
    development: t("svc.development"),
    formation: t("svc.formation"),
  };

  return (
    <Link
      href={`/client/services/${service.id}`}
      className="flex items-center gap-6 border-b border-zx-rule py-5 hover:bg-zx-paper-2 transition-colors px-0"
    >
      <span className="w-36 shrink-0 font-serif italic text-[12px] uppercase tracking-[0.12em] text-zx-green">
        {typeLabel[service.type] ?? service.type}
      </span>
      <div className="flex-1">
        <p className="font-serif text-[17px] text-zx-ink leading-snug mb-2">
          {service.title}
        </p>
        <div className="flex items-center gap-3">
          <div className="h-1.5 flex-1 max-w-xs overflow-hidden rounded-full bg-zx-rule">
            <div
              className="h-full rounded-full bg-zx-green transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="tabular-nums text-[12px] text-zx-ink-mute">
            {progress}%
          </span>
        </div>
      </div>
      <span className="font-serif italic text-[13px] text-zx-ink-mute">
        {service.state}
      </span>
    </Link>
  );
}

export default function ClientDashboardPage() {
  const t = useTranslations();
  const { user } = useAuth();

  const [client, setClient] = useState<ClientRead | null>(null);
  const [services, setServices] = useState<ServiceRead[]>([]);
  const [activity, setActivity] = useState<ActivityLogRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const firstName = user?.display_name?.split(" ")[0] ?? "";

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [clientData, servicesData, activityData] = await Promise.all([
        api.me.getMyClient(),
        api.me.getMyServices(),
        api.me.getMyActivity({ limit: 10 }),
      ]);
      setClient(clientData);
      setServices(servicesData.items);
      setActivity(activityData.items);
    } catch {
      sileo.error({ title: "Error al cargar el portal" });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-pulse text-zx-ink-mute">Cargando...</div>
      </div>
    );
  }

  const activeCount = services.filter(
    (s) => !["lost", "won"].includes(s.state)
  ).length;

  return (
    <div className="-m-10">
      {/* Welcome header */}
      <header className="border-b border-zx-rule px-10 py-8">
        <p className="font-serif italic text-[14px] text-zx-green mb-2">
          — {t("page.client.dashboard.greeting", { name: firstName })}
        </p>
        <h1 className="font-serif text-5xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl">
          {t("page.client.dashboard.title", { client: client?.name ?? "" })}
        </h1>
      </header>

      {/* KPI strip */}
      <div className="grid grid-cols-4 border-b border-zx-rule">
        <KPICard
          label={t("page.client.dashboard.kpi.activeServices")}
          value={activeCount}
        />
        <KPICard
          label={t("page.client.dashboard.kpi.nextMeeting")}
          value="—"
          footnote={t("page.client.dashboard.kpi.nextMeetingFootnote")}
        />
        <KPICard
          label={t("page.client.dashboard.kpi.pendingPayment")}
          value="—"
          footnote={t("page.client.dashboard.kpi.pendingPaymentFootnote")}
        />
        <KPICard
          label={t("page.client.dashboard.kpi.newDocs")}
          value="—"
          footnote={t("page.client.dashboard.kpi.newDocsFootnote")}
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-[1fr_340px]">
        <div className="border-r border-zx-rule">
          {/* Services */}
          <section className="border-b border-zx-rule px-10 py-6">
            <div className="mb-4 flex items-baseline justify-between">
              <h2 className="font-serif text-[22px] text-zx-ink">
                {t("page.client.dashboard.section.services")}
              </h2>
              <Link
                href="/client/projects"
                className="text-[12px] text-zx-green underline underline-offset-2"
              >
                Ver todos →
              </Link>
            </div>
            {services.length === 0 ? (
              <p className="font-serif italic text-zx-ink-mute">
                {t("empty.noServices")}
              </p>
            ) : (
              services.slice(0, 4).map((s) => (
                <ServiceCard key={s.id} service={s} />
              ))
            )}
          </section>

          {/* Activity */}
          <section className="px-10 py-6">
            <h2 className="mb-4 font-serif text-[22px] text-zx-ink">
              {t("page.client.dashboard.section.activity")}
            </h2>
            {activity.length === 0 ? (
              <p className="font-serif italic text-zx-ink-mute">
                {t("empty.noActivity")}
              </p>
            ) : (
              <div>
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="grid grid-cols-[10px_1fr_100px] gap-4 items-start border-b border-zx-rule py-3"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-zx-green" />
                    <div>
                      <p className="font-serif text-[15px] text-zx-ink leading-snug">
                        {item.body}
                      </p>
                    </div>
                    <p className="text-right text-[11px] text-zx-ink-mute tabular-nums">
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Side panel */}
        <aside className="px-7 py-6 space-y-6">
          {/* Team */}
          <div>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute">
              {t("page.client.dashboard.sidepanel.team")}
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-zx-ink text-[11px] font-semibold text-zx-paper">
                  Z
                </div>
                <div>
                  <p className="font-serif text-[14px] text-zx-ink">Zanovix</p>
                  <p className="text-[10.5px] tracking-wide text-zx-ink-mute">
                    Equipo
                  </p>
                </div>
              </div>
            </div>
            <Link
              href="/client/chat"
              className={cn(
                "mt-3 inline-block text-[12px] text-zx-green underline underline-offset-2"
              )}
            >
              Abrir conversación →
            </Link>
          </div>

          {/* Upcoming meetings */}
          <div>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute">
              {t("page.client.dashboard.sidepanel.meetings")}
            </p>
            <p className="font-serif italic text-[13px] text-zx-ink-mute">
              {t("page.client.meetings.comingSoon")}
            </p>
          </div>

          {/* Recent documents */}
          <div>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute">
              {t("page.client.dashboard.sidepanel.documents")}
            </p>
            <p className="font-serif italic text-[13px] text-zx-ink-mute">
              {t("page.client.documents.comingSoon")}
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
