/**
 * Smoke tests for BillingProfileForm.
 *
 * Mock strategy (hoisting-safe): all mock data is inlined inside jest.mock()
 * factory functions — no module-level const references in factories.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ─── Mocks (hoisted) ──────────────────────────────────────────────────────────

jest.mock("next-intl", () => ({
  useTranslations: (namespace?: string) => (key: string) => {
    const dict: Record<string, string> = {
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
      "dialog.editBillingProfile.submit": "Guardar cambios",
      "dialog.editBillingProfile.saving": "Guardando…",
      "dialog.editBillingProfile.cancel": "Cancelar",
    };
    const full = namespace ? `${namespace}.${key}` : key;
    return dict[full] ?? full;
  },
}));

// Mock @radix-ui/react-select so it renders native selects in jsdom
jest.mock("@/components/ui/select", () => ({
  Select: ({ children, value, onValueChange }: { children: React.ReactNode; value: string; onValueChange: (v: string) => void }) => (
    <div data-testid="select-root">
      <select value={value} onChange={(e) => onValueChange(e.target.value)}>
        {children}
      </select>
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

import { BillingProfileForm } from "../billing/BillingProfileForm";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderForm(overrides: Partial<React.ComponentProps<typeof BillingProfileForm>> = {}) {
  const onSubmit = jest.fn();
  const { container } = render(
    <BillingProfileForm
      onSubmit={onSubmit}
      mode="create"
      isSaving={false}
      {...overrides}
    />
  );
  return { container, onSubmit };
}

// ─── Field rendering ──────────────────────────────────────────────────────────

describe("BillingProfileForm — field rendering", () => {
  it("renders legal_name input", () => {
    renderForm();
    expect(screen.getByLabelText("Razón social")).toBeInTheDocument();
  });

  it("renders tax_id input", () => {
    renderForm();
    expect(screen.getByLabelText("Número de identificación")).toBeInTheDocument();
  });

  it("renders address_line1 input", () => {
    renderForm();
    expect(screen.getByLabelText("Dirección (línea 1)")).toBeInTheDocument();
  });

  it("renders city input", () => {
    renderForm();
    expect(screen.getByLabelText("Ciudad")).toBeInTheDocument();
  });

  it("renders province input", () => {
    renderForm();
    expect(screen.getByLabelText("Provincia")).toBeInTheDocument();
  });

  it("renders postal_code input", () => {
    renderForm();
    expect(screen.getByLabelText("Código postal")).toBeInTheDocument();
  });

  it("renders country input defaulting to ES", () => {
    renderForm();
    const countryInput = screen.getByLabelText("País (ISO-2)") as HTMLInputElement;
    expect(countryInput.value).toBe("ES");
  });

  it("renders billing_email input (not required)", () => {
    renderForm();
    expect(screen.getByLabelText("Email de facturación")).toBeInTheDocument();
  });
});

// ─── Required attributes ──────────────────────────────────────────────────────

describe("BillingProfileForm — required attributes", () => {
  it("legal_name is required", () => {
    renderForm();
    const el = screen.getByLabelText("Razón social") as HTMLInputElement;
    expect(el.required).toBe(true);
  });

  it("tax_id is required", () => {
    renderForm();
    const el = screen.getByLabelText("Número de identificación") as HTMLInputElement;
    expect(el.required).toBe(true);
  });

  it("address_line1 is required", () => {
    renderForm();
    const el = screen.getByLabelText("Dirección (línea 1)") as HTMLInputElement;
    expect(el.required).toBe(true);
  });

  it("billing_email is NOT required", () => {
    renderForm();
    const el = screen.getByLabelText("Email de facturación") as HTMLInputElement;
    expect(el.required).toBe(false);
  });
});

// ─── Submit disabled when isSaving ───────────────────────────────────────────

describe("BillingProfileForm — isSaving state", () => {
  it("submit button is disabled when isSaving=true", () => {
    renderForm({ isSaving: true });
    const btn = screen.getByRole("button", { name: /guardando/i });
    expect(btn).toBeDisabled();
  });

  it("submit button is enabled when isSaving=false", () => {
    renderForm();
    const btn = screen.getByRole("button", { name: /crear perfil/i });
    expect(btn).not.toBeDisabled();
  });
});

// ─── Server error display ─────────────────────────────────────────────────────

describe("BillingProfileForm — server validation error display", () => {
  it("shows tax_id server error inline", () => {
    renderForm({ serverErrors: { tax_id: "El NIF no es válido." } });
    expect(screen.getByText("El NIF no es válido.")).toBeInTheDocument();
  });

  it("tax_id input has aria-invalid when server error present", () => {
    renderForm({ serverErrors: { tax_id: "El NIF no es válido." } });
    const el = screen.getByLabelText("Número de identificación") as HTMLInputElement;
    expect(el.getAttribute("aria-invalid")).toBe("true");
  });

  it("does not show error text when serverErrors is empty", () => {
    renderForm({ serverErrors: {} });
    expect(screen.queryByText("El NIF no es válido.")).toBeNull();
  });
});

// ─── hideActions ──────────────────────────────────────────────────────────────

describe("BillingProfileForm — hideActions", () => {
  it("hides the submit button when hideActions=true", () => {
    renderForm({ hideActions: true });
    expect(screen.queryByRole("button", { name: /crear perfil/i })).toBeNull();
  });
});
