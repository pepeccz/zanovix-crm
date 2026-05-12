/**
 * Smoke test: client portal Diagnostic page renders given mocked api.me.*
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/client/diagnostic",
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
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

jest.mock("next-intl", () => ({
  useLocale: () => "es",
  useTranslations: () => (key: string) => key.split(".").pop() ?? key,
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) =>
    <>{children}</>,
}));

jest.mock("sileo", () => ({
  sileo: { error: jest.fn(), success: jest.fn() },
}));

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    me: {
      getMyServices: jest.fn().mockResolvedValue({
        items: [
          {
            id: "s1",
            title: "AI Readiness Assessment",
            type: "assessment",
            state: "delivered",
            progress_pct: 100,
            client_id: "c1",
            owner_id: null,
            created_at: "2024-01-01",
            updated_at: "2024-01-01",
            started_at: null,
            ended_at: null,
            setup_price_cents: null,
            monthly_cents: null,
            score_int: 95,
            milestones: [],
            diagnostic_json: {
              dimensions: {
                data: 80,
                processes: 70,
                team: 65,
                infrastructure: 75,
                compliance: 90,
                leadership: 85,
              },
              plan: [
                { title: "Manifiestos automáticos", status: "go", body: "Alta prioridad" },
                { title: "Previsión demanda", status: "wait", body: "Esperar datos" },
              ],
              summary: "La empresa es sólida técnicamente pero necesita modernizar su infraestructura de datos.",
            },
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      }),
      getMyService: jest.fn().mockResolvedValue({
        id: "s1",
        title: "AI Readiness Assessment",
        type: "assessment",
        state: "delivered",
        progress_pct: 100,
        client_id: "c1",
        owner_id: null,
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
        started_at: null,
        ended_at: null,
        setup_price_cents: null,
        monthly_cents: null,
        score_int: 95,
        milestones: [],
        diagnostic_json: {
          dimensions: {
            data: 80,
            processes: 70,
            team: 65,
            infrastructure: 75,
            compliance: 90,
            leadership: 85,
          },
          plan: [
            { title: "Manifiestos automáticos", status: "go", body: "Alta prioridad" },
            { title: "Previsión demanda", status: "wait", body: "Esperar datos" },
          ],
          summary: "La empresa es sólida técnicamente pero necesita modernizar su infraestructura de datos.",
        },
      }),
    },
  },
}));

// Import AFTER mocks
import DiagnosticPage from "../diagnostic/page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Client Diagnostic — smoke", () => {
  it("renders the composite score", async () => {
    render(<DiagnosticPage />);
    await waitFor(() => {
      // Composite: (80+70+65+75+90+85)/6 = 77
      expect(screen.getByText("77")).toBeInTheDocument();
    });
  });

  it("renders the executive summary", async () => {
    render(<DiagnosticPage />);
    await waitFor(() => {
      expect(
        screen.getByText(/sólida técnicamente/i)
      ).toBeInTheDocument();
    });
  });

  it("renders plan items", async () => {
    render(<DiagnosticPage />);
    await waitFor(() => {
      expect(screen.getByText("Manifiestos automáticos")).toBeInTheDocument();
    });
  });

  it("renders empty state when no assessment service exists", async () => {
    const { default: api } = await import("@/lib/api");
    (api.me.getMyServices as jest.Mock).mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    render(<DiagnosticPage />);
    await waitFor(() => {
      expect(screen.getByText("empty")).toBeInTheDocument();
    });
  });
});
