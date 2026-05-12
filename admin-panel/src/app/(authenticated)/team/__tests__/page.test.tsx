/**
 * Smoke test for /team (Team) page.
 *
 * Strategy: mock api.listUsers + api.getClients + api.getServices and next-intl.
 * Assert PageHeader renders with eyebrow, team member names appear, and
 * metric columns (clients, services, load) are present.
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/team",
}));

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "page.team.eyebrow": "equipo",
    "page.team.title": "Equipo",
    "page.team.lede": "Quién está haciendo qué.",
    "page.team.metric.clients": "Clientes",
    "page.team.metric.services": "Servicios activos",
    "page.team.metric.load": "Carga",
    "page.team.metric.loadPlaceholder": "Disponible próximamente",
    "page.team.role.admin": "Fundador · admin",
    "page.team.role.consultor": "Consultor",
    "page.team.role.comercial": "Comercial",
    "page.team.empty.title": "Equipo vacío",
    "page.team.empty.description": "No hay miembros en el equipo todavía.",
  };
  return {
    useTranslations: () => (key: string) => dict[key] ?? key,
  };
});

const mockListUsers = jest.fn();
const mockGetClients = jest.fn();
const mockGetServices = jest.fn();

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    listUsers: (...args: unknown[]) => mockListUsers(...args),
    getClients: (...args: unknown[]) => mockGetClients(...args),
    getServices: (...args: unknown[]) => mockGetServices(...args),
  },
}));

jest.mock("sileo", () => ({
  sileo: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

// ─── fixtures ────────────────────────────────────────────────────────────────

const USERS = [
  { id: "u-1", display_name: "Ana García", email: "ana@zanovix.com", role: "admin" },
  { id: "u-2", display_name: "Marcos Ruiz", email: "marcos@zanovix.com", role: "consultor" },
];

// ─── tests ───────────────────────────────────────────────────────────────────

describe("/team page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockListUsers.mockResolvedValue({ items: USERS, total: 2 });
    mockGetClients.mockResolvedValue({ items: [], total: 3, limit: 1, offset: 0 });
    mockGetServices.mockResolvedValue({ items: [], total: 5, limit: 1, offset: 0 });
  });

  it("renders the page header with eyebrow", async () => {
    const { default: TeamPage } = await import("../page");
    render(<TeamPage />);
    await waitFor(() => {
      expect(screen.getByText("Equipo")).toBeInTheDocument();
    });
    expect(screen.getByText(/equipo/i, { selector: "p" })).toBeInTheDocument();
  });

  it("renders team member names after loading", async () => {
    const { default: TeamPage } = await import("../page");
    render(<TeamPage />);
    await waitFor(() => {
      expect(screen.getByText("Ana García")).toBeInTheDocument();
      expect(screen.getByText("Marcos Ruiz")).toBeInTheDocument();
    });
  });

  it("renders metric column headings", async () => {
    const { default: TeamPage } = await import("../page");
    render(<TeamPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Clientes").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("Servicios activos").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Carga").length).toBeGreaterThan(0);
  });

  it("shows load placeholder — for each member", async () => {
    const { default: TeamPage } = await import("../page");
    render(<TeamPage />);
    await waitFor(() => {
      // One "—" per member in the load column
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThanOrEqual(USERS.length);
    });
  });
});
