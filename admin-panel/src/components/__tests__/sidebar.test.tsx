/**
 * Tests for Sidebar component.
 *
 * Strategy: mock next/navigation (usePathname), next/image, next/link so
 * jsdom can render without canvas or real routing. Wrap with
 * NextIntlClientProvider supplying the nav.* and sidebar.* keys the
 * component needs.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";

// ─── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/dashboard",
}));

jest.mock("next/image", () => {
  const MockImage = ({
    src,
    alt,
    width,
    height,
  }: {
    src: string;
    alt: string;
    width?: number;
    height?: number;
  }) => <img src={src} alt={alt} width={width} height={height} />;
  MockImage.displayName = "MockImage";
  return MockImage;
});

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

// Import AFTER mocks
import { Sidebar } from "../layout/sidebar";

// ─── Messages fixture ─────────────────────────────────────────────────────────

const messages = {
  nav: {
    dashboard: "Dashboard",
    clients: "Clientes",
    team: "Equipo",
    settings: "Ajustes",
  },
  sidebar: {
    trabajo: "Trabajo",
    personas: "Personas",
    recurrentes: "Recurrentes",
  },
  google: { synced: "Google sincronizado" },
  stripe: { synced: "Stripe sincronizado" },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function renderSidebar() {
  return render(
    <NextIntlClientProvider locale="es" messages={messages}>
      <Sidebar />
    </NextIntlClientProvider>
  );
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Sidebar — brand wordmark", () => {
  it("renders the Zanovix wordmark text", () => {
    renderSidebar();
    expect(screen.getByText("Zanovix")).toBeInTheDocument();
  });
});

describe("Sidebar — nav items", () => {
  it("renders exactly 4 nav links", () => {
    renderSidebar();
    // nav links are <a> elements inside the <nav>; exclude the brand logo link
    const nav = document.querySelector("nav");
    expect(nav).toBeInTheDocument();
    const navLinks = nav!.querySelectorAll("a");
    expect(navLinks).toHaveLength(4);
  });

  it("renders Dashboard nav item", () => {
    renderSidebar();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders Clientes nav item", () => {
    renderSidebar();
    expect(screen.getByText("Clientes")).toBeInTheDocument();
  });

  it("renders Equipo nav item", () => {
    renderSidebar();
    expect(screen.getByText("Equipo")).toBeInTheDocument();
  });

  it("renders Ajustes nav item", () => {
    renderSidebar();
    expect(screen.getByText("Ajustes")).toBeInTheDocument();
  });
});

describe("Sidebar — active item styling", () => {
  it("dashboard link has border-l-2 class when pathname is /dashboard", () => {
    renderSidebar();
    const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
    expect(dashboardLink.className).toContain("border-l-2");
  });

  it("dashboard link has border-zx-green class when active", () => {
    renderSidebar();
    const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
    expect(dashboardLink.className).toContain("border-zx-green");
  });

  it("non-active links have border-transparent class", () => {
    renderSidebar();
    const settingsLink = screen.getByRole("link", { name: /ajustes/i });
    expect(settingsLink.className).toContain("border-transparent");
  });
});
