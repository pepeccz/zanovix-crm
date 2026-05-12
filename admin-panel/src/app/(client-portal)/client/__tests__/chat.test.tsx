/**
 * Smoke test: client portal Chat page renders and polls api.me.getMyMessages
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/client/chat",
}));

jest.mock("next-intl", () => ({
  useLocale: () => "es",
  useTranslations: () => (key: string) => {
    const last = key.split(".").pop() ?? key;
    const map: Record<string, string> = {
      eyebrow: "mensajes",
      title: "Conversación con tu equipo",
      lede: "Directo al equipo.",
      placeholder: "Escribe un mensaje…",
      send: "Enviar",
      empty: "Todavía no hay mensajes.",
      today: "Hoy",
    };
    return map[last] ?? last;
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

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    me: {
      getMyMessages: jest.fn().mockResolvedValue({
        items: [
          {
            id: "m1",
            client_id: "c1",
            sender_user_id: "u-zanovix",
            sender_contact_id: null,
            body: "Hola, ¿cómo podemos ayudarte?",
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      }),
      postMyMessage: jest.fn(),
    },
  },
}));

// Prevent real timers from running during test
jest.useFakeTimers();

// Import AFTER mocks
import ChatPage from "../chat/page";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Client Chat — smoke", () => {
  afterEach(() => {
    jest.clearAllTimers();
  });

  it("renders the chat header", async () => {
    render(<ChatPage />);
    await waitFor(() => {
      expect(screen.getByText("Conversación con tu equipo")).toBeInTheDocument();
    });
  });

  it("renders message from team", async () => {
    render(<ChatPage />);
    await waitFor(() => {
      expect(
        screen.getByText("Hola, ¿cómo podemos ayudarte?")
      ).toBeInTheDocument();
    });
  });

  it("renders the message composer", async () => {
    render(<ChatPage />);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Escribe un mensaje…")
      ).toBeInTheDocument();
    });
  });

  it("renders the Send button", async () => {
    render(<ChatPage />);
    await waitFor(() => {
      expect(screen.getByText("Enviar")).toBeInTheDocument();
    });
  });
});
