/**
 * Tests for StatusPill — CRM stage/state color mapping and i18n label.
 *
 * Mock strategy: same as sidebar.test.tsx — jest.mock("next-intl") with an
 * in-memory dict keyed as `{namespace}.{key}`.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "status.lead": "Lead",
    "status.discovery_scheduled": "Discovery agendada",
    "status.discovery_done": "Discovery realizada",
    "status.proposal_sent": "Propuesta enviada",
    "status.active": "Cliente activo",
    "status.lost": "Perdido",
    "status.scoping": "Definiendo alcance",
    "status.running": "En ejecución",
    "status.delivered": "Entregado",
    "status.won": "Ganado",
    "status.paid": "Pagada",
    "status.pending": "Pendiente",
    "status.overdue": "Vencida",
    "status.draft": "Borrador",
    "status.completed": "Completada",
    "status.development": "Desarrollo",
    "status.review": "En revisión",
    "status.maintenance": "Mantenimiento",
    "status.paused": "Pausado",
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

// Import AFTER mocks
import { StatusPill } from "../shared/status-pill";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function pill(status: string) {
  const { container } = render(<StatusPill status={status} />);
  return container.firstElementChild as HTMLElement;
}

// ─── Label tests ─────────────────────────────────────────────────────────────

describe("StatusPill — i18n labels", () => {
  it("renders translated label for 'active'", () => {
    render(<StatusPill status="active" />);
    expect(screen.getByText("Cliente activo")).toBeInTheDocument();
  });

  it("renders translated label for 'lead'", () => {
    render(<StatusPill status="lead" />);
    expect(screen.getByText("Lead")).toBeInTheDocument();
  });

  it("renders translated label for 'lost'", () => {
    render(<StatusPill status="lost" />);
    expect(screen.getByText("Perdido")).toBeInTheDocument();
  });

  it("falls back to key string for unknown status", () => {
    render(<StatusPill status="unknown_status" />);
    expect(screen.getByText("status.unknown_status")).toBeInTheDocument();
  });
});

// ─── Color class tests ────────────────────────────────────────────────────────

describe("StatusPill — green color group", () => {
  const greenStatuses = ["active", "paid", "completed", "running", "delivered", "won"];

  greenStatuses.forEach((status) => {
    it(`'${status}' has green border class`, () => {
      const el = pill(status);
      expect(el.className).toContain("border-zx-green");
    });

    it(`'${status}' has green text class`, () => {
      const el = pill(status);
      expect(el.className).toContain("text-zx-green-dark");
    });
  });
});

describe("StatusPill — terra color group", () => {
  const terraStatuses = [
    "pending",
    "development",
    "proposal_sent",
    "discovery_scheduled",
    "discovery_done",
    "review",
  ];

  terraStatuses.forEach((status) => {
    it(`'${status}' has terra border class`, () => {
      const el = pill(status);
      expect(el.className).toContain("border-zx-terra");
    });

    it(`'${status}' has terra text class`, () => {
      const el = pill(status);
      expect(el.className).toContain("text-zx-terra");
    });
  });
});

describe("StatusPill — red color group", () => {
  const redStatuses = ["overdue", "lost"];

  redStatuses.forEach((status) => {
    it(`'${status}' has red-600 border class`, () => {
      const el = pill(status);
      expect(el.className).toContain("border-red-600");
    });

    it(`'${status}' has red-600 text class`, () => {
      const el = pill(status);
      expect(el.className).toContain("text-red-600");
    });
  });
});

describe("StatusPill — muted color group", () => {
  const mutedStatuses = ["lead", "draft", "scoping", "paused"];

  mutedStatuses.forEach((status) => {
    it(`'${status}' has muted text class`, () => {
      const el = pill(status);
      expect(el.className).toContain("text-zx-ink-mute");
    });
  });
});

// ─── Structure tests ──────────────────────────────────────────────────────────

describe("StatusPill — structure", () => {
  it("renders as a <span> element", () => {
    const el = pill("active");
    expect(el.tagName).toBe("SPAN");
  });

  it("contains a dot indicator span", () => {
    const { container } = render(<StatusPill status="active" />);
    const spans = container.querySelectorAll("span");
    // outer span + inner dot span
    expect(spans.length).toBeGreaterThanOrEqual(2);
  });

  it("has uppercase text class", () => {
    const el = pill("active");
    expect(el.className).toContain("uppercase");
  });
});
