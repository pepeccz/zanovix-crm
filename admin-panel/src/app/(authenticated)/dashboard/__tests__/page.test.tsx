/**
 * Smoke test for /dashboard page.
 *
 * Strategy:
 * - Mock api.getClients, api.getServices, api.getActivity with fixture data.
 * - Assert the page renders without crashing.
 * - Assert KPI labels are present.
 * - Assert funnel section heading renders.
 * - Assert activity section heading renders.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/dashboard",
}));

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "page.dashboard.eyebrow": "zanovix · panel",
    "page.dashboard.title": "Hoy",
    "page.dashboard.lede": "Lo que merece tu atención antes de las once.",
    "page.dashboard.kpi.mrr": "MRR activo",
    "page.dashboard.kpi.pipelineValue": "Valor en pipeline",
    "page.dashboard.kpi.dealsInMotion": "Tratos en movimiento",
    "page.dashboard.kpi.nextBilling": "Próximo cobro",
    "page.dashboard.kpi.nextBillingFootnote": "Disponible en el módulo de facturación.",
    "page.dashboard.section.funnel": "Embudo comercial",
    "page.dashboard.section.activity": "Actividad reciente",
    "page.dashboard.funnel.empty": "Sin datos de embudo disponibles.",
    "page.dashboard.activity.empty": "Sin actividad reciente.",
    "page.dashboard.error.degraded":
      "Los datos de KPIs y embudo no están disponibles temporalmente.",
    "page.dashboard.error.activityFeed": "No se pudo cargar la actividad reciente.",
    "stage.lead": "Lead",
    "stage.discovery_scheduled": "Discovery agendada",
    "stage.discovery_done": "Discovery realizada",
    "stage.proposal_sent": "Propuesta enviada",
    "stage.active": "Cliente activo",
    "activity.stage_change": "Etapa actualizada",
    "activity.note": "Nota registrada",
  };
  return {
    useTranslations: (namespace?: string) => (key: string) => {
      const full = namespace ? `${namespace}.${key}` : key;
      return dict[full] ?? full;
    },
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
  };
});

// Mock api singleton — fixture data defined inline to avoid hoisting issues
jest.mock("@/lib/api", () => {
  const activeClient = {
    id: "c-active-001",
    name: "Empresa Activa S.A.",
    sector: "Tecnología",
    size: "50-200",
    region: "Barcelona",
    owner_id: "uuid-1234",
    stage: "active",
    entered_at: "2025-06-01T00:00:00Z",
    mrr_cents: 500000,
    lifetime_value_cents: null,
    created_at: "2025-06-01T00:00:00Z",
    updated_at: "2026-01-10T00:00:00Z",
  };
  const leadClient = {
    id: "c-lead-001",
    name: "Lead Corp S.L.",
    sector: "Legal",
    size: "10-50",
    region: "Madrid",
    owner_id: null,
    stage: "lead",
    entered_at: "2026-01-01T00:00:00Z",
    mrr_cents: null,
    lifetime_value_cents: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const service = {
    id: "s-001",
    client_id: "c-active-001",
    title: "AI Assessment",
    type: "assessment",
    state: "running",
    progress_pct: 40,
    owner_id: null,
    score_int: null,
    setup_price_cents: 300000,
    monthly_cents: null,
    started_at: "2026-01-15T00:00:00Z",
    ended_at: null,
    milestones: [],
    created_at: "2026-01-10T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  };
  const activityEntry = {
    id: "act-001",
    created_at: "2026-05-01T10:00:00Z",
    client_id: "c-active-001",
    kind: "stage_change",
    actor_user_id: "uuid-1234",
    body: "lead → active",
  };

  return {
    __esModule: true,
    default: {
      getClients: jest.fn().mockResolvedValue({
        items: [activeClient, leadClient],
        total: 2,
        limit: 200,
        offset: 0,
      }),
      getServices: jest.fn().mockResolvedValue({
        items: [service],
        total: 1,
        limit: 200,
        offset: 0,
      }),
      getActivity: jest.fn().mockResolvedValue({
        items: [activityEntry],
        total: 1,
        limit: 30,
        offset: 0,
      }),
    },
    ApiError: class ApiError extends Error {
      status: number;
      error_code: string;
      allowed: string[] | undefined;
      original: unknown;
      constructor({
        message,
        status,
        error_code,
        allowed,
        original,
      }: {
        message: string;
        status: number;
        error_code: string;
        allowed?: string[];
        original: unknown;
      }) {
        super(message);
        this.status = status;
        this.error_code = error_code;
        this.allowed = allowed;
        this.original = original;
      }
    },
  };
});

// ─── Tests ───────────────────────────────────────────────────────────────────

import DashboardPage from "../page";

describe("DashboardPage — smoke", () => {
  it("renders without crashing and shows KPI labels", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("MRR activo")).toBeInTheDocument();
    });

    expect(screen.getByText("Valor en pipeline")).toBeInTheDocument();
    expect(screen.getByText("Tratos en movimiento")).toBeInTheDocument();
    expect(screen.getByText("Próximo cobro")).toBeInTheDocument();
  });

  it("renders funnel section heading", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Embudo comercial")).toBeInTheDocument();
    });
  });

  it("renders activity feed section with entry body", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Actividad reciente")).toBeInTheDocument();
    });

    // The activity entry body text should appear
    expect(screen.getByText(/lead → active/i)).toBeInTheDocument();
  });
});
