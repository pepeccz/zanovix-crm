/**
 * Smoke test for /clients page.
 *
 * Strategy: mock the api singleton, next/navigation, next-intl, and shared
 * components so the page mounts without real network or routing. Assert
 * the table container is present in the DOM after the fetch resolves.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/clients",
}));

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "page.clients.eyebrow": "el ecosistema",
    "page.clients.title": "Clientes",
    "page.clients.lede": "Cada fila es una empresa.",
    "page.clients.table.name": "Cliente",
    "page.clients.table.stage": "Etapa",
    "page.clients.table.owner": "Responsable",
    "page.clients.table.mrr": "MRR",
    "page.clients.table.next_milestone": "Próximo hito",
    "page.clients.table.contacts": "Contactos",
    "page.clients.filter.allStages": "Todas las etapas",
    "page.clients.filter.allSectors": "Todos los sectores",
    "page.clients.filter.allOwners": "Todos los responsables",
    "page.clients.search.placeholder": "Buscar cliente…",
    "page.clients.empty.title": "Sin clientes",
    "page.clients.empty.description": "No hay clientes.",
    "page.clients.error.title": "Error al cargar los clientes",
    "status.lead": "Lead",
    "status.active": "Cliente activo",
    "status.lost": "Perdido",
    "status.discovery_scheduled": "Discovery agendada",
    "status.discovery_done": "Discovery realizada",
    "status.proposal_sent": "Propuesta enviada",
    "pagination.showing": "Mostrando",
    "pagination.of": "de",
    "pagination.prev": "Anterior",
    "pagination.next": "Siguiente",
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

// Mock api singleton
jest.mock("@/lib/api", () => {
  const mockClient = {
    id: "c-001",
    name: "Empresa Ejemplo S.L.",
    sector: "Legal",
    size: "10-50",
    region: "Madrid",
    owner_id: null,
    stage: "active" as const,
    entered_at: "2026-01-15T10:00:00Z",
    mrr_cents: 250000,
    lifetime_value_cents: null,
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-01-15T10:00:00Z",
  };

  return {
    __esModule: true,
    default: {
      getClients: jest.fn().mockResolvedValue({
        items: [mockClient],
        total: 1,
        limit: 25,
        offset: 0,
      }),
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
import ClientsPage from "../page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("ClientsPage — smoke test", () => {
  it("renders without crashing", async () => {
    render(<ClientsPage />);
    // After load, table should be present
    await waitFor(() => {
      expect(screen.getByText("Empresa Ejemplo S.L.")).toBeInTheDocument();
    });
  });

  it("shows stage header column", async () => {
    render(<ClientsPage />);
    await waitFor(() => {
      expect(screen.getByText("Etapa")).toBeInTheDocument();
    });
  });

  it("shows client name from API response", async () => {
    render(<ClientsPage />);
    await waitFor(() => {
      expect(screen.getByText("Empresa Ejemplo S.L.")).toBeInTheDocument();
    });
  });
});
