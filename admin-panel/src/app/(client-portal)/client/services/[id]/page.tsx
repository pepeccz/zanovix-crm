"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import api from "@/lib/api";
import type { ServiceRead, ActivityLogRead } from "@/lib/types";
import { cn } from "@/lib/utils";
import { sileo } from "sileo";
import { CheckCircle, Clock } from "lucide-react";

export default function ServiceDetailPage() {
  const t = useTranslations();
  const params = useParams();
  const id = params.id as string;

  const [service, setService] = useState<ServiceRead | null>(null);
  const [activity, setActivity] = useState<ActivityLogRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [svcData, actData] = await Promise.all([
        api.me.getMyService(id),
        api.me.getMyActivity({ limit: 20 }),
      ]);
      setService(svcData);
      // Filter activity to this service's client — backend already scopes
      setActivity(actData.items);
    } catch {
      sileo.error({ title: t("page.service_detail.errorLoad") });
    } finally {
      setIsLoading(false);
    }
  }, [id, t]);

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

  if (!service) return null;

  const progress = service.progress_pct ?? 0;

  return (
    <div className="-m-10">
      <header className="border-b border-zx-rule px-10 py-8">
        <div className="mb-2 text-[12px] text-zx-ink-mute">
          <Link href="/client/projects" className="hover:text-zx-ink">
            {t("page.client.projects.title")}
          </Link>
          <span className="mx-2">/</span>
          <span className="text-zx-ink">{service.title}</span>
        </div>
        <p className="font-serif italic text-[14px] text-zx-green mb-2">
          — {t("page.client.service_detail.eyebrow")}
        </p>
        <h1 className="font-serif text-4xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl mb-4">
          {service.title}
        </h1>
        <div className="flex items-center gap-4">
          <span className="rounded-sm border border-zx-rule px-2.5 py-1 text-[12px] uppercase tracking-wide text-zx-ink-mute">
            {service.state}
          </span>
          <div className="flex items-center gap-3">
            <div className="h-1.5 w-48 overflow-hidden rounded-full bg-zx-rule">
              <div
                className="h-full rounded-full bg-zx-green"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="tabular-nums text-[13px] text-zx-ink-mute">
              {progress}%
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_340px]">
        {/* Milestones */}
        <section className="border-b border-r border-zx-rule px-10 py-6">
          <h2 className="mb-4 font-serif text-[22px] text-zx-ink">
            {t("page.client.service_detail.section.milestones")}
          </h2>
          {service.milestones.length === 0 ? (
            <p className="font-serif italic text-zx-ink-mute">
              {t("page.service_detail.emptyMilestones")}
            </p>
          ) : (
            <div>
              {service.milestones.map((m) => (
                <div
                  key={m.id}
                  className="flex items-start gap-4 border-b border-zx-rule py-4"
                >
                  <div className="mt-0.5 shrink-0">
                    {m.completed_at ? (
                      <CheckCircle className="h-4 w-4 text-zx-green" />
                    ) : (
                      <Clock className="h-4 w-4 text-zx-ink-mute" />
                    )}
                  </div>
                  <div>
                    <p
                      className={cn(
                        "font-serif text-[15px]",
                        m.completed_at
                          ? "text-zx-ink-mute line-through"
                          : "text-zx-ink"
                      )}
                    >
                      {m.title}
                    </p>
                    {m.due_date && (
                      <p className="mt-0.5 text-[11px] text-zx-ink-mute">
                        {t("page.service_detail.milestone.dueDate")}:{" "}
                        {new Date(m.due_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Activity side */}
        <section className="border-b border-zx-rule px-7 py-6">
          <h2 className="mb-4 font-serif text-[18px] text-zx-ink">
            {t("page.client.service_detail.section.activity")}
          </h2>
          {activity.length === 0 ? (
            <p className="font-serif italic text-[13px] text-zx-ink-mute">
              {t("page.service_detail.emptyActivity")}
            </p>
          ) : (
            activity.slice(0, 8).map((item) => (
              <div
                key={item.id}
                className="border-b border-zx-rule py-3"
              >
                <p className="text-[13px] text-zx-ink leading-snug">
                  {item.body}
                </p>
                <p className="mt-1 text-[11px] text-zx-ink-mute">
                  {new Date(item.created_at).toLocaleDateString()}
                </p>
              </div>
            ))
          )}
        </section>
      </div>
    </div>
  );
}
