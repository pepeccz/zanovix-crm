/**
 * Smoke test for /services/[id] (Service Detail) page.
 *
 * Strategy: mock api.getService + api.getActivity, next/navigation, next/link,
 * and next-intl. Assert PageHeader, milestones section, state transition button,
 * score section visibility, and activity section render correctly.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "svc-001" }),
  notFound: jest.fn(),
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("next/link", () => {
  const MockLink = ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => <a href={href} className={className}>{children}</a>;
  MockLink.displayName = "MockLink";
  return MockLink;
});

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "page.service_detail.eyebrow": "servicio",
    "page.service_detail.breadcrumb": "Cliente",
    "page.service_detail.section.milestones": "Hitos del servicio",
    "page.service_detail.section.score": "Score de madurez",
    "page.service_detail.section.client": "Cliente",
    "page.service_detail.section.activity": "Actividad reciente",
    "page.service_detail.actions.changeState": "Cambiar estado",
    "page.service_detail.milestone.complete": "Completar",
    "page.service_detail.milestone.dueDate": "Fecha límite",
    "page.service_detail.milestone.completed": "Completado",
    "page.service_detail.milestone.errorToggle": "No se pudo actualizar el hito",
    "page.service_detail.score.outOf": "de 100 · escala Zanovix",
    "page.service_detail.emptyMilestones": "Sin hitos registrados.",
    "page.service_detail.emptyActivity": "Sin actividad reciente.",
    "page.service_detail.viewClient": "Ver cliente",
    "page.service_detail.errorLoad": "Error al cargar el servicio",
    "dialog.serviceStateTransition.trigger": "Cambiar estado",
    "dialog.serviceStateTransition.title": "Cambiar estado del servicio",
    "dialog.serviceStateTransition.description": "Selecciona el siguiente estado.",
    "dialog.serviceStateTransition.confirm": "Confirmar",
    "dialog.serviceStateTransition.cancel": "Cancelar",
    "dialog.serviceStateTransition.error": "No se pudo cambiar el estado",
    "status.scoping": "Scoping",
    "status.running": "En ejecución",
    "status.delivered": "Entregado",
    "status.won": "Ganado",
    "status.lost": "Perdido",
    "serviceType.assessment": "Diagnóstico",
    "serviceType.development": "Desarrollo",
    "serviceType.formation": "Formación",
    "activity.kind.milestone_completed": "Hito completado",
    "activity.kind.stage_change": "Etapa actualizada",
  };
  return {
    useTranslations: (namespace?: string) => (key: string) => {
      const full = namespace ? `${namespace}.${key}` : key;
      return dict[full] ?? full;
    },
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) =>
      <>{children}</>,
  };
});

jest.mock("@/lib/api", () => {
  return {
    __esModule: true,
    default: {
      getService: jest.fn().mockResolvedValue({
        id: "svc-001",
        client_id: "c-001",
        owner_id: "user-abc",
        type: "development",
        title: "Integración API ERP con LangGraph",
        state: "running",
        progress_pct: 65,
        started_at: "2026-03-01T00:00:00Z",
        ended_at: null,
        setup_price_cents: 1800000,
        monthly_cents: 45000,
        score_int: null,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-05-01T12:00:00Z",
        milestones: [
          {
            id: "m-001",
            service_id: "svc-001",
            n: 1,
            title: "Arquitectura validada",
            due_date: "2026-03-22",
            completed_at: "2026-03-20T10:00:00Z",
          },
          {
            id: "m-002",
            service_id: "svc-001",
            n: 2,
            title: "MVP funcional + integraciones",
            due_date: "2026-04-19",
            completed_at: null,
          },
        ],
      }),
      getActivity: jest.fn().mockResolvedValue({
        items: [
          {
            id: "act-001",
            created_at: "2026-05-09T10:00:00Z",
            client_id: "c-001",
            kind: "milestone_completed",
            actor_user_id: null,
            body: "Arquitectura validada completada",
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }),
      patchServiceState: jest.fn(),
      patchMilestone: jest.fn(),
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

// Import AFTER mocks
import ServiceDetailPage from "../page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("ServiceDetailPage — smoke test", () => {
  it("renders the service title as page header", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      // Title appears in both the h1 and the breadcrumb span — use getAllByText
      const matches = screen.getAllByText("Integración API ERP con LangGraph");
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it("renders the Milestones section heading", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Hitos del servicio")).toBeInTheDocument();
    });
  });

  it("renders milestone titles", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Arquitectura validada")).toBeInTheDocument();
      expect(
        screen.getByText("MVP funcional + integraciones")
      ).toBeInTheDocument();
    });
  });

  it("renders the state transition button", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Cambiar estado")).toBeInTheDocument();
    });
  });

  it("does NOT render Score section for non-assessment service", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Hitos del servicio")).toBeInTheDocument();
    });
    expect(screen.queryByText("Score de madurez")).not.toBeInTheDocument();
  });

  it("renders Complete button for incomplete milestones", async () => {
    render(<ServiceDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Completar")).toBeInTheDocument();
    });
  });
});
