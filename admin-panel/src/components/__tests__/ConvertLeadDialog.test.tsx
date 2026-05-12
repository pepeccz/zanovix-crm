/**
 * Smoke tests for ConvertLeadDialog — billing accordion integration.
 *
 * Mock strategy (hoisting-safe): all mock data inlined inside jest.mock()
 * factory functions. api.convertLead is a jest.fn() spy.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// ─── Mocks (hoisted) ──────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("next-intl", () => ({
  useTranslations: (namespace?: string) => (key: string) => {
    const dict: Record<string, string> = {
      "dialog.convertLead.trigger": "Convertir",
      "dialog.convertLead.title": "Convertir lead a cliente",
      "dialog.convertLead.description": "Campos opcionales.",
      "dialog.convertLead.fields.name": "Nombre del cliente",
      "dialog.convertLead.fields.sector": "Sector",
      "dialog.convertLead.fields.size": "Tamaño",
      "dialog.convertLead.fields.region": "Región",
      "dialog.convertLead.fields.stage": "Etapa inicial",
      "dialog.convertLead.fields.mrr": "MRR (€/mes)",
      "dialog.convertLead.section.billing.title": "Datos de facturación",
      "dialog.convertLead.section.billing.description": "Opcional.",
      "dialog.convertLead.submit": "Convertir",
      "dialog.convertLead.saving": "Convirtiendo…",
      "dialog.convertLead.cancel": "Cancelar",
      "dialog.convertLead.success": "Lead convertido",
      "dialog.convertLead.error": "No se pudo convertir el lead",
      "dialog.convertLead.alreadyConverted": "Ya convertido.",
      "dialog.convertLead.mustBeQualified": "Debe estar calificado.",
      "dialog.convertLead.notQualifiedTooltip": "Solo calificados.",
      "dialog.billingProfileForm.fields.legal_name": "Razón social",
      "dialog.billingProfileForm.fields.tax_id_type": "Tipo de identificación",
      "dialog.billingProfileForm.fields.tax_id": "Número de identificación",
      "dialog.billingProfileForm.fields.tax_regime": "Régimen fiscal",
      "dialog.billingProfileForm.fields.address_line1": "Dirección (línea 1)",
      "dialog.billingProfileForm.fields.address_line2": "Dirección (línea 2)",
      "dialog.billingProfileForm.fields.city": "Ciudad",
      "dialog.billingProfileForm.fields.province": "Provincia",
      "dialog.billingProfileForm.fields.postal_code": "Código postal",
      "dialog.billingProfileForm.fields.country": "País (ISO-2)",
      "dialog.billingProfileForm.fields.billing_email": "Email de facturación",
      "dialog.billingProfileForm.tax_id_type.NIF": "NIF",
      "dialog.billingProfileForm.tax_id_type.CIF": "CIF",
      "dialog.billingProfileForm.tax_id_type.NIE": "NIE",
      "dialog.billingProfileForm.tax_id_type.VAT": "VAT (UE)",
      "dialog.billingProfileForm.tax_regime.general": "Régimen general",
      "dialog.billingProfileForm.tax_regime.recargo_equivalencia": "Recargo de equivalencia",
      "dialog.billingProfileForm.tax_regime.simplificado": "Régimen simplificado",
      "dialog.billingProfileForm.tax_regime.exento": "Exento",
      "dialog.billingProfileForm.tax_regime.intracomunitario": "Intracomunitario",
      "dialog.newBillingProfile.submit": "Crear perfil",
      "dialog.newBillingProfile.saving": "Guardando…",
      "dialog.newBillingProfile.cancel": "Cancelar",
      "status.lead": "Lead",
      "status.discovery_scheduled": "Discovery agendada",
      "status.discovery_done": "Discovery realizada",
      "status.proposal_sent": "Propuesta enviada",
      "status.active": "Cliente activo",
      "status.lost": "Perdido",
    };
    const full = namespace ? `${namespace}.${key}` : key;
    return dict[full] ?? full;
  },
}));

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    convertLead: jest.fn().mockResolvedValue({
      id: "client-new",
      name: "Test Client",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      sector: null, size: null, region: null, owner_id: null,
      stage: "lead", entered_at: "2026-01-01T00:00:00Z",
      mrr_cents: null, lifetime_value_cents: null,
    }),
  },
  ApiError: class ApiError extends Error {
    status: number;
    error_code: string;
    allowed: undefined;
    original: unknown;
    constructor({ message, status, error_code, original }: { message: string; status: number; error_code: string; original: unknown }) {
      super(message);
      this.status = status;
      this.error_code = error_code;
      this.original = original;
    }
  },
}));

jest.mock("sileo", () => ({
  sileo: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("@/components/ui/select", () => ({
  Select: ({ children, value, onValueChange }: { children: React.ReactNode; value: string; onValueChange: (v: string) => void }) => (
    <div data-testid="select-root">
      <select value={value} onChange={(e) => onValueChange(e.target.value)}>{children}</select>
    </div>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectValue: () => null,
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({ value, children }: { value: string; children: React.ReactNode }) => (
    <option value={value}>{children}</option>
  ),
}));

// ─── Import AFTER mocks ────────────────────────────────────────────────────────

import { ConvertLeadDialog } from "../shared/convert-lead-dialog";
import api from "@/lib/api";
import type { Lead } from "@/lib/types";

// ─── Fixtures (safe: defined after imports) ────────────────────────────────────

const mockLead: Lead = {
  id: "lead-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  name: "Juan García",
  email: "juan@example.com",
  phone: null,
  company: "Empresa SL",
  vertical: "general",
  channel: "web_form",
  source_url: null,
  notes: null,
  status: "qualified",
  owner_id: null,
  role: "CEO",
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ConvertLeadDialog — trigger", () => {
  it("renders the trigger button", () => {
    render(<ConvertLeadDialog lead={mockLead} />);
    expect(screen.getByRole("button", { name: "Convertir" })).toBeInTheDocument();
  });

  it("opens the dialog when trigger is clicked", () => {
    render(<ConvertLeadDialog lead={mockLead} />);
    fireEvent.click(screen.getByRole("button", { name: "Convertir" }));
    expect(screen.getByText("Convertir lead a cliente")).toBeInTheDocument();
  });
});

describe("ConvertLeadDialog — without billing accordion", () => {
  it("calls convertLead WITHOUT billing_profile when accordion is not expanded", async () => {
    render(<ConvertLeadDialog lead={mockLead} />);

    // Open dialog
    fireEvent.click(screen.getByRole("button", { name: "Convertir" }));

    // Submit without opening billing accordion
    const submitBtn = screen.getByRole("button", { name: "Convertir" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.convertLead).toHaveBeenCalledWith(
        "lead-1",
        expect.objectContaining({
          billing_profile: expect.oneOf ? expect.anything() : undefined,
        })
      );
    });

    // Specifically check billing_profile is null/undefined — not a filled object
    const callArgs = (api.convertLead as jest.Mock).mock.calls[0];
    const body = callArgs[1];
    expect(body.billing_profile == null).toBe(true);
  });
});

describe("ConvertLeadDialog — billing accordion section visible", () => {
  it("shows the billing accordion section title when dialog is open", () => {
    render(<ConvertLeadDialog lead={mockLead} />);
    fireEvent.click(screen.getByRole("button", { name: "Convertir" }));
    expect(screen.getByText("Datos de facturación")).toBeInTheDocument();
  });
});
