/**
 * Tests for LocaleToggle component.
 *
 * Strategy: mock next/navigation (useRouter) and next-intl (useLocale).
 * Wrap with NextIntlClientProvider to satisfy the intl context.
 * Verify active-state styling and cookie + refresh side effects on click.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────
// next-intl ships pure ESM; mock it to avoid Jest transform chain issues.

const mockRefresh = jest.fn();
let currentLocale: "es" | "en" = "es";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
  usePathname: () => "/dashboard",
}));

jest.mock("next-intl", () => ({
  useLocale: () => currentLocale,
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = { langES: "ES", langEN: "EN" };
    return map[key] ?? key;
  },
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Import AFTER mocks
import { LocaleToggle } from "../layout/locale-toggle";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function renderToggle(locale: "es" | "en" = "es") {
  currentLocale = locale;
  return render(<LocaleToggle />);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("LocaleToggle — active state", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders both ES and EN buttons", () => {
    renderToggle("es");
    expect(screen.getByRole("button", { name: /es/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /en/i })).toBeInTheDocument();
  });

  it("ES button has aria-pressed=true when locale is es", () => {
    renderToggle("es");
    const esBtn = screen.getByRole("button", { name: /es/i });
    const enBtn = screen.getByRole("button", { name: /en/i });
    expect(esBtn).toHaveAttribute("aria-pressed", "true");
    expect(enBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("EN button has aria-pressed=true when locale is en", () => {
    renderToggle("en");
    const esBtn = screen.getByRole("button", { name: /es/i });
    const enBtn = screen.getByRole("button", { name: /en/i });
    expect(enBtn).toHaveAttribute("aria-pressed", "true");
    expect(esBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("active locale button has bg-zx-green class", () => {
    renderToggle("es");
    const esBtn = screen.getByRole("button", { name: /es/i });
    expect(esBtn.className).toContain("bg-zx-green");
  });

  it("inactive locale button does not have bg-zx-green class", () => {
    renderToggle("es");
    const enBtn = screen.getByRole("button", { name: /en/i });
    expect(enBtn.className).not.toContain("bg-zx-green");
  });
});

describe("LocaleToggle — click interaction", () => {
  let cookieStore = "";

  beforeEach(() => {
    jest.clearAllMocks();
    cookieStore = "";
    Object.defineProperty(document, "cookie", {
      configurable: true,
      get: () => cookieStore,
      set: (val: string) => {
        cookieStore = val;
      },
    });
  });

  it("clicking EN button writes zx-locale=en to document.cookie", () => {
    renderToggle("es");
    const enBtn = screen.getByRole("button", { name: /en/i });
    fireEvent.click(enBtn);
    expect(cookieStore).toContain("zx-locale=en");
  });

  it("clicking EN button calls router.refresh()", () => {
    renderToggle("es");
    const enBtn = screen.getByRole("button", { name: /en/i });
    fireEvent.click(enBtn);
    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it("clicking the already-active locale does not call router.refresh()", () => {
    renderToggle("es");
    const esBtn = screen.getByRole("button", { name: /es/i });
    fireEvent.click(esBtn);
    expect(mockRefresh).not.toHaveBeenCalled();
  });
});
