/**
 * Smoke tests for BillingProfileList.
 *
 * Mock strategy (hoisting-safe): all mock data inlined inside jest.mock()
 * factory functions. api methods are mocked at module level via jest.mock().
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ─── Mocks (hoisted) ──────────────────────────────────────────────────────────

jest.mock("next-intl", () => ({
  useTranslations: (namespace?: string) => (key: string) => {
    const dict: Record<string, string> = {
      "page.client_detail.billing.default_badge": "Por defecto",
      "page.client_detail.billing.set_default": "Establecer por defecto",
      "page.client_detail.billing.edit": "Editar",
      "page.client_detail.billing.delete": "Eliminar",
      "page.client_detail.billing.confirm_delete": "¿Eliminar este perfil?",
      "page.client_detail.billing.empty_state": "Sin perfiles de facturación.",
      "dialog.newBillingProfile.title": "Nuevo perfil",
      "dialog.newBillingProfile.submit": "Crear perfil",
      "dialog.newBillingProfile.saving": "Guardando…",
      "dialog.newBillingProfile.cancel": "Cancelar",
      "dialog.editBillingProfile.title": "Editar perfil",
      "dialog.editBillingProfile.submit": "Guardar cambios",
      "dialog.editBillingProfile.saving": "Guardando…",
      "dialog.editBillingProfile.cancel": "Cancelar",
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
    };
    const full = namespace ? `${namespace}.${key}` : key;
    return dict[full] ?? full;
  },
}));

jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    setDefaultBillingProfile: jest.fn().mockResolvedValue({ id: "profile-1", is_default: true }),
    deleteBillingProfile: jest.fn().mockResolvedValue(undefined),
    updateBillingProfile: jest.fn().mockResolvedValue({ id: "profile-1" }),
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

import { BillingProfileList } from "../billing/BillingProfileList";
import api from "@/lib/api";
import type { BillingProfile } from "@/lib/types";

// ─── Fixtures (safe: defined after imports, not in factory scope) ─────────────

const profileDefault: BillingProfile = {
  id: "profile-1",
  client_id: "client-1",
  legal_name: "Acme SL",
  tax_id: "B12345674",
  tax_id_type: "CIF",
  tax_regime: "general",
  address_line1: "Calle Mayor 1",
  address_line2: null,
  city: "Madrid",
  province: "Madrid",
  postal_code: "28001",
  country: "ES",
  billing_email: null,
  is_default: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const profileSecondary: BillingProfile = {
  ...profileDefault,
  id: "profile-2",
  legal_name: "Beta SA",
  tax_id: "A87654321",
  tax_id_type: "NIF",
  is_default: false,
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("BillingProfileList — empty state", () => {
  it("renders empty state text when profiles list is empty", () => {
    render(
      <BillingProfileList clientId="client-1" profiles={[]} onMutate={jest.fn()} />
    );
    expect(screen.getByText("Sin perfiles de facturación.")).toBeInTheDocument();
  });
});

describe("BillingProfileList — default badge", () => {
  it("renders default badge on the default profile", () => {
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileDefault]}
        onMutate={jest.fn()}
      />
    );
    expect(screen.getByText("Por defecto")).toBeInTheDocument();
  });

  it("does not render default badge on non-default profile", () => {
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileSecondary]}
        onMutate={jest.fn()}
      />
    );
    expect(screen.queryByText("Por defecto")).toBeNull();
  });
});

describe("BillingProfileList — set default action", () => {
  it("calls setDefaultBillingProfile and onMutate when 'Establecer por defecto' is clicked", async () => {
    const onMutate = jest.fn();
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileDefault, profileSecondary]}
        onMutate={onMutate}
      />
    );

    // Only the non-default profile should show "Establecer por defecto"
    const setDefaultBtn = screen.getByRole("button", {
      name: "Establecer por defecto",
    });
    fireEvent.click(setDefaultBtn);

    await waitFor(() => {
      expect(api.setDefaultBillingProfile).toHaveBeenCalledWith("profile-2");
      expect(onMutate).toHaveBeenCalled();
    });
  });

  it("does not show 'Establecer por defecto' for the default profile", () => {
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileDefault]}
        onMutate={jest.fn()}
      />
    );
    // The default profile should NOT have the set-default button
    expect(
      screen.queryByRole("button", { name: "Establecer por defecto" })
    ).toBeNull();
  });
});

describe("BillingProfileList — profile details", () => {
  it("renders legal name", () => {
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileDefault]}
        onMutate={jest.fn()}
      />
    );
    expect(screen.getByText("Acme SL")).toBeInTheDocument();
  });

  it("renders tax_id_type and tax_id", () => {
    render(
      <BillingProfileList
        clientId="client-1"
        profiles={[profileDefault]}
        onMutate={jest.fn()}
      />
    );
    expect(screen.getByText(/CIF B12345674/)).toBeInTheDocument();
  });
});
