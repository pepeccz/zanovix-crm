/**
 * Smoke test for /clients/[id] (Client 360) page.
 *
 * Strategy: mock api.getClient, next/navigation (useParams), next/link,
 * and next-intl. Assert PageHeader, contacts section, and services section
 * render correctly.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "c-001" }),
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
    "page.client_detail.breadcrumb": "Clientes",
    "page.client_detail.section.contacts": "Contactos",
    "page.client_detail.section.services": "Servicios activos",
    "page.client_detail.section.activity": "Actividad reciente",
    "page.client_detail.actions.changeStage": "Cambiar etapa",
    "page.client_detail.emptyContacts": "Sin contactos registrados.",
    "page.client_detail.emptyServices": "Aún sin servicios.",
    "page.client_detail.emptyActivity": "Sin actividad reciente.",
    "dialog.stageTransition.trigger": "Cambiar etapa",
    "dialog.stageTransition.title": "Cambiar etapa del cliente",
    "dialog.stageTransition.description": "Selecciona la siguiente etapa.",
    "dialog.stageTransition.confirm": "Confirmar",
    "dialog.stageTransition.cancel": "Cancelar",
    "dialog.stageTransition.error": "No se pudo cambiar la etapa",
    "status.active": "Cliente activo",
    "status.lead": "Lead",
    "status.lost": "Perdido",
    "status.running": "En ejecución",
    "status.discovery_scheduled": "Discovery agendada",
    "serviceType.assessment": "Diagnóstico",
    "serviceType.development": "Desarrollo",
    "serviceType.formation": "Formación",
    "activity.stage_change": "Etapa actualizada",
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
  const mockDetail = {
    id: "c-001",
    name: "Naviera SAP S.A.",
    sector: "Logística",
    size: "200-500",
    region: "Barcelona",
    owner_id: "user-abc",
    stage: "active" as const,
    entered_at: "2026-01-10T09:00:00Z",
    mrr_cents: 380000,
    lifetime_value_cents: null,
    created_at: "2026-01-10T09:00:00Z",
    updated_at: "2026-05-01T12:00:00Z",
    contacts: [
      {
        id: "con-001",
        client_id: "c-001",
        name: "Inés Berrocal",
        role: "CTO",
        email: "ines@naviera.es",
        phone: "+34 600 000 001",
        is_primary: true,
        created_at: "2026-01-10T09:00:00Z",
        updated_at: "2026-01-10T09:00:00Z",
      },
    ],
    services: [
      {
        id: "svc-001",
        title: "Integración API ERP",
        type: "development" as const,
        state: "running" as const,
        progress_pct: 65,
        owner_id: null,
      },
    ],
    recent_activity: [
      {
        id: "act-001",
        created_at: "2026-05-09T10:00:00Z",
        client_id: "c-001",
        kind: "stage_change" as const,
        actor_user_id: null,
        body: "Lead → active",
      },
    ],
  };

  return {
    __esModule: true,
    default: {
      getClient: jest.fn().mockResolvedValue(mockDetail),
      patchClientStage: jest.fn(),
    },
    ApiError: class ApiError extends Error {
      status: number;
      error_code: string;
      allowed: string[] | undefined;
      original: unknown;
      constructor({ message, status, error_code, allowed, original }: {
        message: string; status: number; error_code: string;
        allowed?: string[]; original: unknown;
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
import ClientDetailPage from "../[id]/page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("ClientDetailPage — smoke test", () => {
  it("renders the client name as page header", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Naviera SAP S.A.")).toBeInTheDocument();
    });
  });

  it("renders the Contacts section heading", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Contactos")).toBeInTheDocument();
    });
  });

  it("renders the Services section heading", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Servicios activos")).toBeInTheDocument();
    });
  });

  it("renders a contact name", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Inés Berrocal")).toBeInTheDocument();
    });
  });

  it("renders a service title", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Integración API ERP")).toBeInTheDocument();
    });
  });

  it("renders the stage transition button", async () => {
    render(<ClientDetailPage />);
    await waitFor(() => {
      expect(screen.getByText("Cambiar etapa")).toBeInTheDocument();
    });
  });
});
