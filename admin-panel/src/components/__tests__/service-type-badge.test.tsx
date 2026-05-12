/**
 * Tests for ServiceTypeBadge — 3 service types, icon + i18n label.
 *
 * Mock strategy: same as sidebar.test.tsx — jest.mock("next-intl").
 * Lucide icons render as SVG elements; we verify by aria-label or container structure.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next-intl", () => {
  const dict: Record<string, string> = {
    "serviceType.assessment": "Diagnóstico",
    "serviceType.development": "Desarrollo",
    "serviceType.formation": "Formación",
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
import { ServiceTypeBadge } from "../shared/service-type-badge";

// ─── Label tests ─────────────────────────────────────────────────────────────

describe("ServiceTypeBadge — i18n labels", () => {
  it("renders 'Diagnóstico' for assessment", () => {
    render(<ServiceTypeBadge type="assessment" />);
    expect(screen.getByText("Diagnóstico")).toBeInTheDocument();
  });

  it("renders 'Desarrollo' for development", () => {
    render(<ServiceTypeBadge type="development" />);
    expect(screen.getByText("Desarrollo")).toBeInTheDocument();
  });

  it("renders 'Formación' for formation", () => {
    render(<ServiceTypeBadge type="formation" />);
    expect(screen.getByText("Formación")).toBeInTheDocument();
  });
});

// ─── Color class tests ────────────────────────────────────────────────────────

describe("ServiceTypeBadge — color classes", () => {
  it("assessment uses green-dark text", () => {
    const { container } = render(<ServiceTypeBadge type="assessment" />);
    expect(container.firstElementChild?.className).toContain("text-zx-green-dark");
  });

  it("development uses ink text", () => {
    const { container } = render(<ServiceTypeBadge type="development" />);
    expect(container.firstElementChild?.className).toContain("text-zx-ink");
  });

  it("formation uses terra text", () => {
    const { container } = render(<ServiceTypeBadge type="formation" />);
    expect(container.firstElementChild?.className).toContain("text-zx-terra");
  });

  it("all types have bg-zx-paper-2 background", () => {
    (["assessment", "development", "formation"] as const).forEach((type) => {
      const { container } = render(<ServiceTypeBadge type={type} />);
      expect(container.firstElementChild?.className).toContain("bg-zx-paper-2");
    });
  });
});

// ─── Icon tests ───────────────────────────────────────────────────────────────

describe("ServiceTypeBadge — Lucide icons", () => {
  it("renders an SVG icon for each type", () => {
    (["assessment", "development", "formation"] as const).forEach((type) => {
      const { container } = render(<ServiceTypeBadge type={type} />);
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });
});

// ─── Structure tests ──────────────────────────────────────────────────────────

describe("ServiceTypeBadge — structure", () => {
  it("renders as a <span> element", () => {
    const { container } = render(<ServiceTypeBadge type="assessment" />);
    expect(container.firstElementChild?.tagName).toBe("SPAN");
  });

  it("renders icon and label together", () => {
    const { container } = render(<ServiceTypeBadge type="assessment" />);
    const span = container.firstElementChild as HTMLElement;
    const svg = span.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(span.textContent).toContain("Diagnóstico");
  });
});
