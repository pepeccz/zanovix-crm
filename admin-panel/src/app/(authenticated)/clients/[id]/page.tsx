"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Star, Phone, Mail, ChevronRight, ExternalLink } from "lucide-react";
import { sileo } from "sileo";
import api, { ApiError } from "@/lib/api";
import type { ClientDetailResponse, ClientRead } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatusPill } from "@/components/shared/status-pill";
import { ServiceTypeBadge } from "@/components/shared/service-type-badge";
import { ProgressBar } from "@/components/shared/progress-bar";
import { ActivityTimelineItem } from "@/components/shared/activity-timeline-item";
import { StageTransitionDialog } from "@/components/shared/stage-transition-dialog";
import { cn } from "@/lib/utils";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("page.client_detail");

  const [client, setClient] = useState<ClientDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFoundError, setNotFoundError] = useState(false);

  const fetchClient = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.getClient(id);
      setClient(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFoundError(true);
      } else {
        console.error("Error fetching client:", err);
        sileo.error({
          title: "Error al cargar el cliente",
          description: err instanceof Error ? err.message : "Error desconocido",
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchClient();
  }, [fetchClient]);

  function handleStageSuccess(updated: ClientRead) {
    setClient((prev) =>
      prev ? { ...prev, stage: updated.stage, updated_at: updated.updated_at } : prev
    );
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

  if (!client) return null;

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 px-10 py-4 text-[12px] text-zx-ink-mute">
        <Link href="/clients" className="hover:text-zx-ink transition-colors">
          {t("breadcrumb") ?? "Clientes"}
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-zx-ink">{client.name}</span>
      </nav>

      {/* Page Header */}
      <PageHeader
        eyebrow={client.sector ?? undefined}
        title={client.name}
        lede={[client.region, client.size].filter(Boolean).join(" · ") || undefined}
        right={
          <div className="flex items-center gap-3">
            <StatusPill status={client.stage} />
            <StageTransitionDialog
              clientId={client.id}
              currentStage={client.stage}
              onSuccess={handleStageSuccess}
            />
          </div>
        }
      />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-0 border-t border-zx-rule">
        {/* Main column */}
        <div className="border-r border-zx-rule">
          {/* Servicios activos */}
          <section className="border-b border-zx-rule">
            <div className="px-10 py-5 border-b border-zx-rule/50">
              <h2 className="font-serif text-xl text-zx-ink">
                {t("section.services")}
              </h2>
            </div>

            {client.services.length === 0 ? (
              <div className="px-10 py-10 text-center">
                <p className="font-serif italic text-base text-zx-ink-mute">
                  {t("emptyServices")}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-zx-rule/50">
                {client.services.map((service) => (
                  <Link
                    key={service.id}
                    href={`/services/${service.id}`}
                    className="flex items-center gap-6 px-10 py-4 hover:bg-zx-paper-2/50 transition-colors group"
                  >
                    <ServiceTypeBadge type={service.type} />

                    <div className="flex-1 min-w-0">
                      <div className="font-serif text-[15px] text-zx-ink leading-snug">
                        {service.title}
                      </div>
                      <div className="mt-2 flex items-center gap-3">
                        <ProgressBar
                          value={service.progress_pct ?? 0}
                          className="max-w-[200px]"
                        />
                        <span className="text-[11px] text-zx-ink-mute tabular-nums">
                          {service.progress_pct ?? 0}%
                        </span>
                      </div>
                    </div>

                    <StatusPill status={service.state} />

                    <ExternalLink className="h-4 w-4 text-zx-ink-mute opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Actividad reciente */}
          <section>
            <div className="px-10 py-5 border-b border-zx-rule/50">
              <h2 className="font-serif text-xl text-zx-ink">
                {t("section.activity")}
              </h2>
            </div>

            {client.recent_activity.length === 0 ? (
              <div className="px-10 py-10 text-center">
                <p className="font-serif italic text-base text-zx-ink-mute">
                  {t("emptyActivity")}
                </p>
              </div>
            ) : (
              <div className="px-10 py-2">
                {client.recent_activity.slice(0, 20).map((entry) => (
                  <ActivityTimelineItem key={entry.id} entry={entry} />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Sidebar — Contactos */}
        <aside className="px-8 py-6">
          <h2 className="font-serif text-xl text-zx-ink mb-4">
            {t("section.contacts")}
          </h2>

          {client.contacts.length === 0 ? (
            <p className="font-serif italic text-sm text-zx-ink-mute">
              {t("emptyContacts")}
            </p>
          ) : (
            <div className="divide-y divide-zx-rule/50">
              {client.contacts.map((contact) => (
                <div key={contact.id} className="py-3">
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-serif text-[15px] text-zx-ink">
                          {contact.name}
                        </span>
                        {contact.is_primary && (
                          <Star
                            className="h-3 w-3 text-zx-terra shrink-0"
                            aria-label="Contacto principal"
                          />
                        )}
                      </div>
                      {contact.role && (
                        <p className="text-[11.5px] text-zx-ink-soft mt-0.5">
                          {contact.role}
                        </p>
                      )}
                      {contact.email && (
                        <a
                          href={`mailto:${contact.email}`}
                          className="flex items-center gap-1 text-[11.5px] text-zx-green mt-1 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Mail className="h-3 w-3 shrink-0" />
                          {contact.email}
                        </a>
                      )}
                      {contact.phone && (
                        <a
                          href={`tel:${contact.phone}`}
                          className="flex items-center gap-1 text-[11.5px] text-zx-ink-soft mt-0.5 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Phone className="h-3 w-3 shrink-0" />
                          {contact.phone}
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Owner section */}
          {client.owner_id && (
            <div className={cn("mt-8 pt-6 border-t border-zx-rule")}>
              <h3 className="text-[10.5px] uppercase tracking-[0.18em] text-zx-ink-mute mb-3">
                Responsable
              </h3>
              <div className="flex items-center gap-2.5">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zx-ink text-[12px] font-medium text-zx-paper">
                  {client.owner_id.slice(0, 2).toUpperCase()}
                </span>
                <span className="text-xs text-zx-ink-soft font-mono">
                  {client.owner_id.slice(0, 12)}
                </span>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
