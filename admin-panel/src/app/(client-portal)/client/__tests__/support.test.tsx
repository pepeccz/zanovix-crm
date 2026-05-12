/**
 * Smoke test: client portal Support page renders ticket list and new ticket dialog
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/client/support",
}));

jest.mock("next-intl", () => ({
  useLocale: () => "es",
  useTranslations: () => (key: string) => {
    const last = key.split(".").pop() ?? key;
    const map: Record<string, string> = {
      eyebrow: "soporte",
      title: "Tickets de soporte",
      lede: "¿Algo no va bien?",
      newTicket: "Nuevo ticket",
      all: "Todos",
      pending: "Pendiente",
      in_progress: "En curso",
      closed: "Cerrado",
      empty: "No hay tickets.",
      submit: "Enviar ticket",
      cancel: "Cancelar",
      error: "No se pudo crear el ticket",
    };
    return map[last] ?? last;
  },
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
      getMyTickets: jest.fn().mockResolvedValue({
        items: [
          {
            id: "t1",
            client_id: "c1",
            service_id: null,
            title: "No puedo acceder al dashboard",
            priority: "high",
            status: "pending",
            created_at: "2024-05-01T10:00:00Z",
            updated_at: "2024-05-01T10:00:00Z",
          },
          {
            id: "t2",
            client_id: "c1",
            service_id: null,
            title: "Pregunta sobre factura INV-041",
            priority: "medium",
            status: "in_progress",
            created_at: "2024-04-20T09:00:00Z",
            updated_at: "2024-04-21T11:00:00Z",
          },
        ],
        total: 2,
        limit: 50,
        offset: 0,
      }),
      postMyTicket: jest.fn(),
    },
  },
}));

// Import AFTER mocks
import SupportPage from "../support/page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Client Support — smoke", () => {
  it("renders the page title", async () => {
    render(<SupportPage />);
    await waitFor(() => {
      expect(screen.getByText("Tickets de soporte")).toBeInTheDocument();
    });
  });

  it("renders the new ticket button", async () => {
    render(<SupportPage />);
    await waitFor(() => {
      expect(screen.getByText("Nuevo ticket")).toBeInTheDocument();
    });
  });

  it("renders ticket titles from API", async () => {
    render(<SupportPage />);
    await waitFor(() => {
      expect(
        screen.getByText("No puedo acceder al dashboard")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Pregunta sobre factura INV-041")
      ).toBeInTheDocument();
    });
  });

  it("renders filter chips", async () => {
    render(<SupportPage />);
    await waitFor(() => {
      expect(screen.getByText("Todos")).toBeInTheDocument();
      expect(screen.getByText("Pendiente")).toBeInTheDocument();
      expect(screen.getByText("En curso")).toBeInTheDocument();
    });
  });
});
