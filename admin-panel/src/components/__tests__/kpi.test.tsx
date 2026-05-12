/**
 * Tests for KPI component — label/value, delta, footnote.
 *
 * KPI has no i18n (label is passed as a prop), so no next-intl mock needed.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// Import after any mocks (none needed here)
import { KPI } from "../shared/kpi";

// ─── Label + Value ────────────────────────────────────────────────────────────

describe("KPI — label and value", () => {
  it("renders the label text", () => {
    render(<KPI label="MRR" value="€12.400" />);
    expect(screen.getByText("MRR")).toBeInTheDocument();
  });

  it("renders the value text", () => {
    render(<KPI label="MRR" value="€12.400" />);
    expect(screen.getByText("€12.400")).toBeInTheDocument();
  });

  it("value element has font-serif class", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" />);
    const valueEl = container.querySelector(".font-serif.tabular-nums");
    expect(valueEl).toBeInTheDocument();
  });

  it("label has uppercase tracking class", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" />);
    const labelEl = container.querySelector("p.uppercase");
    expect(labelEl).toBeInTheDocument();
    expect(labelEl?.textContent).toBe("MRR");
  });
});

// ─── Delta ───────────────────────────────────────────────────────────────────

describe("KPI — delta prop", () => {
  it("renders positive delta text", () => {
    render(<KPI label="MRR" value="€12.400" delta="+8%" />);
    expect(screen.getByText("+8%")).toBeInTheDocument();
  });

  it("renders negative delta text", () => {
    render(<KPI label="MRR" value="€12.400" delta="−12%" />);
    expect(screen.getByText("−12%")).toBeInTheDocument();
  });

  it("positive delta has green color class", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" delta="+8%" />);
    const deltaEl = container.querySelector(".text-zx-green");
    expect(deltaEl).toBeInTheDocument();
    expect(deltaEl?.textContent).toBe("+8%");
  });

  it("negative delta (−) has terra color class", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" delta="−12%" />);
    const deltaEl = container.querySelector(".text-zx-terra");
    expect(deltaEl).toBeInTheDocument();
    expect(deltaEl?.textContent).toBe("−12%");
  });

  it("negative delta (-) has terra color class", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" delta="-12%" />);
    const deltaEl = container.querySelector(".text-zx-terra");
    expect(deltaEl).toBeInTheDocument();
  });

  it("does not render delta element when omitted", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" />);
    const deltaEl = container.querySelector(".text-zx-terra, .text-zx-green");
    expect(deltaEl).toBeNull();
  });
});

// ─── Footnote ─────────────────────────────────────────────────────────────────

describe("KPI — footnote prop", () => {
  it("renders footnote text when provided", () => {
    render(<KPI label="MRR" value="€12.400" footnote="vs mes anterior" />);
    expect(screen.getByText("vs mes anterior")).toBeInTheDocument();
  });

  it("footnote element has italic serif class", () => {
    const { container } = render(
      <KPI label="MRR" value="€12.400" footnote="vs mes anterior" />
    );
    const footnoteEl = container.querySelector("p.italic");
    expect(footnoteEl).toBeInTheDocument();
    expect(footnoteEl?.textContent).toBe("vs mes anterior");
  });

  it("does not render footnote element when omitted", () => {
    const { container } = render(<KPI label="MRR" value="€12.400" />);
    // No italic <p> (label is a <p> but not italic)
    const italicP = container.querySelector("p.italic");
    expect(italicP).toBeNull();
  });
});
