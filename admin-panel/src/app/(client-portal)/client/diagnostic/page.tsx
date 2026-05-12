"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import api from "@/lib/api";
import type { ServiceRead, DiagnosticDimensions } from "@/lib/types";
import { sileo } from "sileo";

const DIMENSION_KEYS: (keyof DiagnosticDimensions)[] = [
  "data",
  "processes",
  "team",
  "infrastructure",
  "compliance",
  "leadership",
];

const DIMENSION_LABELS: Record<keyof DiagnosticDimensions, string> = {
  data: "Datos",
  processes: "Procesos",
  team: "Equipo",
  infrastructure: "Infraestructura",
  compliance: "Cumplimiento",
  leadership: "Liderazgo",
};

function DimensionBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="py-3 border-b border-zx-rule">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[13px] text-zx-ink">{label}</span>
        <span className="tabular-nums text-[13px] font-semibold text-zx-ink">
          {value}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zx-rule">
        <div
          className="h-full rounded-full bg-zx-green transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function DiagnosticPage() {
  const t = useTranslations();
  const [service, setService] = useState<ServiceRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const servicesData = await api.me.getMyServices();
      const assessmentService = servicesData.items.find(
        (s) => s.type === "assessment"
      );
      if (!assessmentService) {
        setNotFound(true);
        return;
      }
      const detail = await api.me.getMyService(assessmentService.id);
      if (!detail.diagnostic_json) {
        setNotFound(true);
        return;
      }
      setService(detail);
    } catch {
      sileo.error({ title: "Error al cargar el diagnóstico" });
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

  if (notFound || !service?.diagnostic_json) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <p className="font-serif italic text-xl text-zx-ink-mute">
          {t("page.client.diagnostic.empty")}
        </p>
      </div>
    );
  }

  const diag = service.diagnostic_json;
  const dims = diag.dimensions;
  const compositeScore = Math.round(
    DIMENSION_KEYS.reduce((sum, k) => sum + dims[k], 0) /
      DIMENSION_KEYS.length
  );

  const planByStatus = {
    go: diag.plan.filter((p) => p.status === "go"),
    wait: diag.plan.filter((p) => p.status === "wait"),
    skip: diag.plan.filter((p) => p.status === "skip"),
  };

  const statusLabel: Record<string, string> = {
    go: t("page.client.diagnostic.plan.go"),
    wait: t("page.client.diagnostic.plan.wait"),
    skip: t("page.client.diagnostic.plan.skip"),
  };

  const statusColor: Record<string, string> = {
    go: "text-zx-green border-zx-green",
    wait: "text-amber-700 border-amber-700",
    skip: "text-zx-ink-mute border-zx-ink-mute",
  };

  return (
    <div className="-m-10">
      <header className="border-b border-zx-rule px-10 py-8">
        <p className="font-serif italic text-[14px] text-zx-green mb-2">
          — {t("page.client.diagnostic.eyebrow")}
        </p>
        <h1 className="font-serif text-5xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl mb-4">
          {t("page.client.diagnostic.title")}
        </h1>
        <p className="font-serif italic text-[18px] text-zx-ink-mute max-w-2xl leading-relaxed">
          {t("page.client.diagnostic.lede")}
        </p>
      </header>

      {/* Composite score */}
      <section className="border-b border-zx-rule px-10 py-8">
        <div className="flex items-end gap-4">
          <span className="font-serif text-[96px] leading-none text-zx-green font-light">
            {compositeScore}
          </span>
          <span className="font-serif italic text-[20px] text-zx-ink-mute mb-4">
            {t("page.client.diagnostic.score.outOf")}
          </span>
        </div>
      </section>

      {/* Dimensions */}
      <section className="border-b border-zx-rule px-10 py-8">
        <h2 className="mb-4 font-serif text-[22px] text-zx-ink">
          {t("page.client.diagnostic.section.dimensions")}
        </h2>
        <div className="max-w-lg">
          {DIMENSION_KEYS.map((k) => (
            <DimensionBar
              key={k}
              label={DIMENSION_LABELS[k]}
              value={dims[k]}
            />
          ))}
        </div>
      </section>

      {/* Executive summary */}
      <section className="border-b border-zx-rule px-10 py-8">
        <h2 className="mb-4 font-serif text-[22px] text-zx-ink">
          {t("page.client.diagnostic.section.summary")}
        </h2>
        <p className="font-serif text-[18px] leading-relaxed text-zx-ink max-w-3xl">
          {diag.summary}
        </p>
      </section>

      {/* Plan */}
      <section className="border-b border-zx-rule px-10 py-8">
        <h2 className="mb-6 font-serif text-[22px] text-zx-ink">
          {t("page.client.diagnostic.section.plan")}
        </h2>
        {(["go", "wait", "skip"] as const).map((status) =>
          planByStatus[status].length > 0 ? (
            <div key={status} className="mb-6">
              <p
                className={`mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                  status === "go"
                    ? "text-zx-green"
                    : status === "wait"
                    ? "text-amber-700"
                    : "text-zx-ink-mute"
                }`}
              >
                {statusLabel[status]}
              </p>
              {planByStatus[status].map((item, i) => (
                <div key={i} className="border-b border-zx-rule py-4">
                  <div className="flex items-start gap-4">
                    <span
                      className={`mt-0.5 shrink-0 rounded-sm border px-2 py-0.5 text-[11px] uppercase tracking-wide ${statusColor[status]}`}
                    >
                      {statusLabel[status]}
                    </span>
                    <div>
                      <p className="font-serif text-[17px] text-zx-ink">
                        {item.title}
                      </p>
                      <p className="mt-1 text-[13px] text-zx-ink-mute leading-relaxed">
                        {item.body}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null
        )}
      </section>

      {/* CTA */}
      <div className="mx-10 my-10 bg-zx-night text-zx-paper rounded-sm px-14 py-12">
        <p className="font-serif italic text-[14px] text-zx-green mb-3">
          — {t("page.client.diagnostic.cta.proposal")}
        </p>
        <Link
          href="/client/chat"
          className="inline-block rounded-sm border border-zx-paper/30 px-5 py-2.5 font-sans text-[13px] tracking-wide text-zx-paper hover:bg-zx-paper/10 transition-colors"
        >
          {t("page.client.diagnostic.cta.proposal")} →
        </Link>
      </div>
    </div>
  );
}
