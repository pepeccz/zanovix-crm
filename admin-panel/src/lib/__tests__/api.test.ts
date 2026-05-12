/**
 * Unit tests for ApiClient CRM methods and ApiError class.
 *
 * All tests mock global `fetch`. The api singleton is reset before each test
 * by setting a fresh token (or null) so tests stay isolated.
 */

import api, { ApiError } from "../api";

// ─── helpers ────────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown): void {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

function mockFetch204(): void {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 204,
    headers: { get: (h: string) => (h === "content-length" ? "0" : null) },
    json: () => Promise.reject(new Error("no body")),
  } as unknown as Response);
}

function lastUrl(): string {
  return (global.fetch as jest.Mock).mock.calls[0][0] as string;
}

function lastOptions(): RequestInit {
  return (global.fetch as jest.Mock).mock.calls[0][1] as RequestInit;
}

// ─── setup ──────────────────────────────────────────────────────────────────

beforeEach(() => {
  api.setToken("test-token");
});

afterEach(() => {
  jest.resetAllMocks();
});

// ─── ApiError class ─────────────────────────────────────────────────────────

describe("ApiError", () => {
  it("extends Error and preserves message", () => {
    const err = new ApiError({
      message: "something went wrong",
      status: 409,
      error_code: "invalid_transition",
      allowed: ["active", "lost"],
      original: { error: "invalid_transition", allowed: ["active", "lost"] },
    });

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("something went wrong");
    expect(err.status).toBe(409);
    expect(err.error_code).toBe("invalid_transition");
    expect(err.allowed).toEqual(["active", "lost"]);
  });

  it("is thrown by _doRequest on 4xx", async () => {
    mockFetch(404, { detail: "Client not found" });
    await expect(api.getClient("missing-id")).rejects.toBeInstanceOf(ApiError);
  });

  it("carries status and error_code from 409 body", async () => {
    mockFetch(409, {
      error: "invalid_transition",
      from: "active",
      to: "lead",
      allowed: ["lost"],
    });

    try {
      await api.patchClientStage("some-id", "lead");
      fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(409);
      expect(apiErr.error_code).toBe("invalid_transition");
      expect(apiErr.allowed).toEqual(["lost"]);
    }
  });

  it("carries message from FastAPI 422 detail array", async () => {
    mockFetch(422, {
      detail: [{ msg: "field required", type: "missing" }],
    });

    try {
      await api.getClients();
      fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).message).toBe("field required");
      expect((err as ApiError).status).toBe(422);
    }
  });
});

// ─── Clients ─────────────────────────────────────────────────────────────────

describe("getClients", () => {
  it("calls GET /api/clients with no params when filters empty", async () => {
    mockFetch(200, { items: [], total: 0, limit: 50, offset: 0 });
    await api.getClients();
    expect(lastUrl()).toBe("/api/clients");
  });

  it("builds query string from filters", async () => {
    mockFetch(200, { items: [], total: 0, limit: 25, offset: 0 });
    await api.getClients({ stage: "active", limit: 25, offset: 0, q: "acme" });
    const url = lastUrl();
    expect(url).toContain("stage=active");
    expect(url).toContain("limit=25");
    expect(url).toContain("q=acme");
  });
});

describe("getClient", () => {
  it("calls GET /api/clients/{id}", async () => {
    const detail = {
      id: "abc",
      contacts: [],
      services: [],
      recent_activity: [],
    };
    mockFetch(200, detail);
    const result = await api.getClient("abc");
    expect(lastUrl()).toBe("/api/clients/abc");
    expect(result).toEqual(detail);
  });
});

describe("createClient", () => {
  it("calls POST /api/clients with JSON body", async () => {
    mockFetch(201, { id: "new-id", name: "Test" });
    await api.createClient({ name: "Test" });
    expect(lastUrl()).toBe("/api/clients");
    expect(lastOptions().method).toBe("POST");
    expect(JSON.parse(lastOptions().body as string)).toEqual({ name: "Test" });
  });
});

describe("patchClient", () => {
  it("calls PATCH /api/clients/{id}", async () => {
    mockFetch(200, { id: "id-1", name: "Updated" });
    await api.patchClient("id-1", { name: "Updated" });
    expect(lastUrl()).toBe("/api/clients/id-1");
    expect(lastOptions().method).toBe("PATCH");
  });
});

describe("patchClientStage", () => {
  it("calls PATCH /api/clients/{id}/stage with stage payload", async () => {
    mockFetch(200, { id: "id-1", stage: "active" });
    await api.patchClientStage("id-1", "active");
    expect(lastUrl()).toBe("/api/clients/id-1/stage");
    expect(lastOptions().method).toBe("PATCH");
    expect(JSON.parse(lastOptions().body as string)).toEqual({ stage: "active" });
  });
});

// ─── Contacts ────────────────────────────────────────────────────────────────

describe("getClientContacts", () => {
  it("calls GET /api/clients/{clientId}/contacts", async () => {
    mockFetch(200, []);
    await api.getClientContacts("client-1");
    expect(lastUrl()).toBe("/api/clients/client-1/contacts");
  });
});

describe("createContact", () => {
  it("calls POST /api/clients/{clientId}/contacts", async () => {
    mockFetch(201, { id: "c-1", name: "Alice" });
    await api.createContact("client-1", {
      client_id: "client-1",
      name: "Alice",
    });
    expect(lastUrl()).toBe("/api/clients/client-1/contacts");
    expect(lastOptions().method).toBe("POST");
  });
});

describe("patchContact", () => {
  it("calls PATCH /api/clients/{clientId}/contacts/{contactId}", async () => {
    mockFetch(200, { id: "c-1", name: "Bob" });
    await api.patchContact("client-1", "c-1", { name: "Bob" });
    expect(lastUrl()).toBe("/api/clients/client-1/contacts/c-1");
    expect(lastOptions().method).toBe("PATCH");
  });
});

describe("deleteContact", () => {
  it("calls DELETE /api/clients/{clientId}/contacts/{contactId}", async () => {
    mockFetch204();
    await api.deleteContact("client-1", "c-1");
    expect(lastUrl()).toBe("/api/clients/client-1/contacts/c-1");
    expect(lastOptions().method).toBe("DELETE");
  });
});

// ─── Services ────────────────────────────────────────────────────────────────

describe("getServices", () => {
  it("calls GET /api/services with no params when filters empty", async () => {
    mockFetch(200, { items: [], total: 0, limit: 50, offset: 0 });
    await api.getServices();
    expect(lastUrl()).toBe("/api/services");
  });

  it("builds query string for service filters", async () => {
    mockFetch(200, { items: [], total: 0, limit: 10, offset: 0 });
    await api.getServices({ state: "running", type: "assessment", limit: 10 });
    const url = lastUrl();
    expect(url).toContain("state=running");
    expect(url).toContain("type=assessment");
    expect(url).toContain("limit=10");
  });
});

describe("getService", () => {
  it("calls GET /api/services/{id}", async () => {
    mockFetch(200, { id: "svc-1", milestones: [] });
    await api.getService("svc-1");
    expect(lastUrl()).toBe("/api/services/svc-1");
  });
});

describe("createService", () => {
  it("calls POST /api/clients/{clientId}/services", async () => {
    mockFetch(201, { id: "svc-new" });
    await api.createService("client-1", { type: "assessment", title: "Q1 Audit" });
    expect(lastUrl()).toBe("/api/clients/client-1/services");
    expect(lastOptions().method).toBe("POST");
    const body = JSON.parse(lastOptions().body as string);
    expect(body.type).toBe("assessment");
    expect(body.client_id).toBe("client-1");
  });
});

describe("patchService", () => {
  it("calls PATCH /api/services/{id}", async () => {
    mockFetch(200, { id: "svc-1", title: "Renamed" });
    await api.patchService("svc-1", { title: "Renamed" });
    expect(lastUrl()).toBe("/api/services/svc-1");
    expect(lastOptions().method).toBe("PATCH");
  });
});

describe("patchServiceState", () => {
  it("calls PATCH /api/services/{id}/state with state payload", async () => {
    mockFetch(200, { id: "svc-1", state: "running" });
    await api.patchServiceState("svc-1", "running");
    expect(lastUrl()).toBe("/api/services/svc-1/state");
    expect(JSON.parse(lastOptions().body as string)).toEqual({ state: "running" });
  });
});

// ─── Milestones ───────────────────────────────────────────────────────────────

describe("getMilestones", () => {
  it("calls GET /api/services/{serviceId}/milestones", async () => {
    mockFetch(200, []);
    await api.getMilestones("svc-1");
    expect(lastUrl()).toBe("/api/services/svc-1/milestones");
  });
});

describe("createMilestone", () => {
  it("calls POST /api/services/{serviceId}/milestones", async () => {
    mockFetch(201, { id: "m-1", n: 1 });
    await api.createMilestone("svc-1", { n: 1, title: "Kickoff" });
    expect(lastUrl()).toBe("/api/services/svc-1/milestones");
    expect(lastOptions().method).toBe("POST");
  });
});

describe("patchMilestone", () => {
  it("calls PATCH /api/services/{serviceId}/milestones/{n}", async () => {
    mockFetch(200, { id: "m-1", n: 1, completed_at: "2026-05-12T00:00:00Z" });
    await api.patchMilestone("svc-1", 1, { completed_at: "2026-05-12T00:00:00Z" });
    expect(lastUrl()).toBe("/api/services/svc-1/milestones/1");
    expect(lastOptions().method).toBe("PATCH");
  });
});

describe("deleteMilestone", () => {
  it("calls DELETE /api/services/{serviceId}/milestones/{n}", async () => {
    mockFetch204();
    await api.deleteMilestone("svc-1", 2);
    expect(lastUrl()).toBe("/api/services/svc-1/milestones/2");
    expect(lastOptions().method).toBe("DELETE");
  });
});

// ─── Lead conversion ─────────────────────────────────────────────────────────

describe("convertLead", () => {
  it("calls POST /api/leads/{leadId}/convert", async () => {
    mockFetch(201, { id: "client-new" });
    await api.convertLead("lead-1");
    expect(lastUrl()).toBe("/api/leads/lead-1/convert");
    expect(lastOptions().method).toBe("POST");
  });

  it("sends optional body fields when provided", async () => {
    mockFetch(201, { id: "client-new" });
    await api.convertLead("lead-1", { name: "Acme Corp", sector: "tech" });
    const body = JSON.parse(lastOptions().body as string);
    expect(body.name).toBe("Acme Corp");
    expect(body.sector).toBe("tech");
  });
});

// ─── Activity ─────────────────────────────────────────────────────────────────

describe("getActivity", () => {
  it("calls GET /api/activity with no params by default", async () => {
    mockFetch(200, { items: [], total: 0, limit: 50, offset: 0 });
    await api.getActivity();
    expect(lastUrl()).toBe("/api/activity");
  });

  it("builds query string for limit and offset", async () => {
    mockFetch(200, { items: [], total: 0, limit: 30, offset: 0 });
    await api.getActivity({ limit: 30, offset: 0 });
    const url = lastUrl();
    expect(url).toContain("limit=30");
    expect(url).toContain("offset=0");
  });

  it("includes client_id in query string when provided", async () => {
    mockFetch(200, { items: [], total: 0, limit: 50, offset: 0 });
    await api.getActivity({ client_id: "client-99" });
    expect(lastUrl()).toContain("client_id=client-99");
  });
});
