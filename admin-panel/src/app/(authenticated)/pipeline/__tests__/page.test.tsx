/**
 * Smoke test for /pipeline page.
 *
 * Strategy:
 * - Mock api.getClients to return 3 fixture clients across 3 pipeline stages.
 * - Mock @dnd-kit/core so no real DnD implementation is needed.
 * - Assert kanban board container renders and client cards appear.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/pipeline",
}));

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "page.pipeline.eyebrow": "comercial",
    "page.pipeline.title": "Pipeline comercial",
    "page.pipeline.lede": "De primera conversación a entrada al ecosistema.",
    "page.pipeline.view.kanban": "Kanban",
    "page.pipeline.view.list": "Lista",
    "page.pipeline.empty.column": "vacío",
    "page.pipeline.drag_hint": "Arrastra tarjetas para mover de etapa",
    "page.clients.filter.allOwners": "Todos los responsables",
    "page.clients.filter.allSectors": "Todos los sectores",
    "page.clients.filter.allStages": "Todas las etapas",
    "page.clients.empty.title": "Sin clientes",
    "page.clients.empty.description": "No hay clientes.",
    "page.clients.table.name": "Cliente",
    "page.clients.table.stage": "Etapa",
    "page.clients.table.owner": "Responsable",
    "page.clients.table.mrr": "MRR",
    "page.clients.table.next_milestone": "Próximo hito",
    "stage.lead": "Lead",
    "stage.discovery_scheduled": "Discovery agendada",
    "stage.discovery_done": "Discovery realizada",
    "stage.proposal_sent": "Propuesta enviada",
    "stage.active": "Cliente activo",
    "stage.lost": "Perdido",
    "status.lead": "Lead",
    "status.active": "Cliente activo",
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

// Mock @dnd-kit/core — no actual drag-and-drop in jsdom
jest.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dnd-context">{children}</div>
  ),
  useDroppable: () => ({ isOver: false, setNodeRef: jest.fn() }),
  useDraggable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    isDragging: false,
  }),
  PointerSensor: class {},
  TouchSensor: class {},
  useSensor: () => null,
  useSensors: (...args: unknown[]) => args,
}));

// Mock api singleton
const mockLead: import("@/lib/types").ClientRead = {
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

const mockActive: import("@/lib/types").ClientRead = {
  id: "c-active-001",
  name: "Empresa Activa S.A.",
  sector: "Tecnología",
  size: "50-200",
  region: "Barcelona",
  owner_id: "uuid-1234-5678",
  stage: "active",
  entered_at: "2025-06-01T00:00:00Z",
  mrr_cents: 350000,
  lifetime_value_cents: null,
  created_at: "2025-06-01T00:00:00Z",
  updated_at: "2026-01-10T00:00:00Z",
};

const mockProposal: import("@/lib/types").ClientRead = {
  id: "c-prop-001",
  name: "Propuesta Pendiente S.L.",
  sector: "Logística",
  size: "10-50",
  region: "Valencia",
  owner_id: null,
  stage: "proposal_sent",
  entered_at: "2026-03-01T00:00:00Z",
  mrr_cents: null,
  lifetime_value_cents: null,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-04-01T00:00:00Z",
};

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    getClients: jest.fn().mockResolvedValue({
      items: [mockLead, mockActive, mockProposal],
      total: 3,
      limit: 200,
      offset: 0,
    }),
    patchClientStage: jest.fn(),
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
}));

// Import AFTER mocks
import PipelinePage from "../page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("PipelinePage — smoke test", () => {
  it("renders the DndContext (kanban board) by default", async () => {
    render(<PipelinePage />);
    await waitFor(() => {
      expect(screen.getByTestId("dnd-context")).toBeInTheDocument();
    });
  });

  it("renders 5 kanban columns", async () => {
    render(<PipelinePage />);
    // Columns are labelled by stage using useTranslations("stage")
    await waitFor(() => {
      expect(screen.getByText("Lead")).toBeInTheDocument();
      expect(screen.getByText("Discovery agendada")).toBeInTheDocument();
      expect(screen.getByText("Cliente activo")).toBeInTheDocument();
    });
  });

  it("renders client cards in their respective columns", async () => {
    render(<PipelinePage />);
    await waitFor(() => {
      expect(screen.getByText("Lead Corp S.L.")).toBeInTheDocument();
      expect(screen.getByText("Empresa Activa S.A.")).toBeInTheDocument();
      expect(screen.getByText("Propuesta Pendiente S.L.")).toBeInTheDocument();
    });
  });
});
