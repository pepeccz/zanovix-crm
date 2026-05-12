/**
 * Smoke test: client portal Dashboard page renders given mocked api.me.*
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/client",
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
  useTranslations: () => (key: string, params?: Record<string, string>) => {
    if (params?.name) return `hola, ${params.name}`;
    if (params?.client) return `Bienvenido ${params.client}`;
    return key.split(".").pop() ?? key;
  },
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) =>
    <>{children}</>,
}));

jest.mock("sileo", () => ({
  sileo: { error: jest.fn(), success: jest.fn() },
}));

jest.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: { id: "u1", email: "test@test.com", display_name: "Ana García", role: "client_user" },
    isLoading: false,
    isAuthenticated: true,
  }),
}));

const mockClient = {
  id: "c1",
  name: "Naviera Med",
  stage: "active" as const,
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  sector: null,
  size: null,
  region: null,
  owner_id: null,
  entered_at: "2024-01-01",
  mrr_cents: null,
  lifetime_value_cents: null,
};

const mockServices = {
  items: [
    {
      id: "s1",
      title: "AI Readiness Assessment",
      type: "assessment" as const,
      state: "running" as const,
      progress_pct: 75,
      client_id: "c1",
      owner_id: null,
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
      started_at: null,
      ended_at: null,
      setup_price_cents: null,
      monthly_cents: null,
      score_int: null,
      milestones: [],
      diagnostic_json: null,
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const mockActivity = { items: [], total: 0, limit: 20, offset: 0 };

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    me: {
      getMyClient: jest.fn().mockResolvedValue(mockClient),
      getMyServices: jest.fn().mockResolvedValue(mockServices),
      getMyActivity: jest.fn().mockResolvedValue(mockActivity),
    },
  },
}));

// Import AFTER mocks
import ClientDashboardPage from "../page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Client Dashboard — smoke", () => {
  it("renders the welcome greeting", async () => {
    render(<ClientDashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/hola, Ana/i)).toBeInTheDocument();
    });
  });

  it("renders KPI cards", async () => {
    render(<ClientDashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("activeServices")).toBeInTheDocument();
    });
  });

  it("renders service card title", async () => {
    render(<ClientDashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("AI Readiness Assessment")).toBeInTheDocument();
    });
  });
});
