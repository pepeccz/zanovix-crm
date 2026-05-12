"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import api from "@/lib/api";
import type { ServiceRead } from "@/lib/types";
import { sileo } from "sileo";

function ServiceTypeBadge({ type }: { type: string }) {
  const t = useTranslations();
  const typeLabel: Record<string, string> = {
    assessment: t("svc.assessment"),
    development: t("svc.development"),
    formation: t("svc.formation"),
  };
  const typeColor: Record<string, string> = {
    assessment: "text-zx-green border-zx-green",
    development: "text-zx-ink border-zx-ink",
    formation: "text-amber-700 border-amber-700",
  };
  return (
    <span
      className={`inline-block rounded-sm border px-2 py-0.5 text-[11px] uppercase tracking-[0.1em] ${
        typeColor[type] ?? "text-zx-ink-mute border-zx-rule"
      }`}
    >
      {typeLabel[type] ?? type}
    </span>
  );
}

export default function ProjectsPage() {
  const t = useTranslations();
  const [services, setServices] = useState<ServiceRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.me.getMyServices();
      setServices(data.items);
    } catch {
      sileo.error({ title: "Error al cargar los servicios" });
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

  return (
    <div className="-m-10">
      <header className="border-b border-zx-rule px-10 py-8">
        <p className="font-serif italic text-[14px] text-zx-green mb-2">
          — {t("page.client.projects.eyebrow")}
        </p>
        <h1 className="font-serif text-5xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl mb-4">
          {t("page.client.projects.title")}
        </h1>
        <p className="font-serif italic text-[18px] text-zx-ink-mute max-w-2xl leading-relaxed">
          {t("page.client.projects.lede")}
        </p>
      </header>

      <div className="px-10 py-6">
        {services.length === 0 ? (
          <p className="font-serif italic text-zx-ink-mute">
            {t("page.client.projects.empty")}
          </p>
        ) : (
          services.map((service) => {
            const progress = service.progress_pct ?? 0;
            return (
              <Link
                key={service.id}
                href={`/client/services/${service.id}`}
                className="grid grid-cols-[160px_1fr_130px] items-center gap-6 border-b border-zx-rule py-5 hover:bg-zx-paper-2 transition-colors"
              >
                <ServiceTypeBadge type={service.type} />
                <div>
                  <p className="font-serif text-[17px] text-zx-ink leading-snug mb-2">
                    {service.title}
                  </p>
                  <div className="flex items-center gap-3">
                    <div className="h-1.5 flex-1 max-w-xs overflow-hidden rounded-full bg-zx-rule">
                      <div
                        className="h-full rounded-full bg-zx-green"
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
          })
        )}
      </div>
    </div>
  );
}
