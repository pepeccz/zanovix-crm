/**
 * Smoke test for AppShell component.
 *
 * Strategy: mock Sidebar and Topbar (they have their own unit tests) to
 * isolate the grid composition logic. Assert that AppShell renders children
 * and applies the grid layout class to the root element.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/dashboard",
}));

jest.mock("../layout/sidebar", () => ({
  Sidebar: () => <div data-testid="mock-sidebar" />,
}));

jest.mock("../layout/topbar", () => ({
  Topbar: () => <div data-testid="mock-topbar" />,
}));

// Import AFTER mocks
import { AppShell } from "../layout/app-shell";

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("AppShell — smoke test", () => {
  it("renders children in the document", () => {
    render(
      <AppShell>
        <div data-testid="child-content">hello</div>
      </AppShell>
    );
    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("renders a <main> element", () => {
    render(
      <AppShell>
        <span>content</span>
      </AppShell>
    );
    const main = document.querySelector("main");
    expect(main).toBeInTheDocument();
  });

  it("root element has grid class", () => {
    const { container } = render(
      <AppShell>
        <span>content</span>
      </AppShell>
    );
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toContain("grid");
  });

  it("renders the mock Sidebar", () => {
    render(
      <AppShell>
        <span>content</span>
      </AppShell>
    );
    expect(screen.getByTestId("mock-sidebar")).toBeInTheDocument();
  });

  it("renders the mock Topbar", () => {
    render(
      <AppShell>
        <span>content</span>
      </AppShell>
    );
    expect(screen.getByTestId("mock-topbar")).toBeInTheDocument();
  });
});
