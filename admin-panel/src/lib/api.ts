/**
 * API Client for Zanovix CRM Admin Panel
 * Handles all HTTP requests to FastAPI backend
 */

import type {
  ActivityFilters,
  ActivityLogListResponse,
  ClientDetailResponse,
  ClientFilters,
  ClientListResponse,
  ClientRead,
  ClientStage,
  ClientUpdate,
  ContactCreate,
  ContactRead,
  ContactUpdate,
  ConvertLeadBody,
  CurrentUser,
  Diagnostic,
  Lead,
  LeadListResponse,
  LeadStatus,
  Message,
  MessageCreate,
  MessageListResponse,
  MilestoneCreate,
  MilestoneRead,
  MilestoneUpdate,
  ServiceFilters,
  ServiceListResponse,
  ServiceRead,
  ServiceState,
  ServiceType,
  ServiceUpdate,
  Ticket,
  TicketCreate,
  TicketListResponse,
  TicketPatch,
  TicketStatus,
  UserListResponse,
} from "./types";

// Usa URL relativa - Next.js rewrites hace proxy al backend
const API_BASE_URL = "";

/** In-flight GET request deduplication map (module-scoped, lightweight) */
const inflight = new Map<string, Promise<unknown>>();

/**
 * Typed API error — thrown by ApiClient for all non-2xx responses.
 *
 * Extends Error so existing code that reads `.message` keeps working.
 * Callers that need to branch on error kind should check `.status` and `.body`.
 *
 * For 409 invalid_transition responses the backend returns:
 *   { error: "invalid_transition", from, to, allowed: string[] }
 * Callers can read `(err.body as Record<string, unknown>).allowed` to get the list.
 */
export class ApiError extends Error {
  /** HTTP status code (e.g. 400, 403, 404, 409, 422, 500). */
  status: number;
  /**
   * The `error` field from the response JSON envelope, when present.
   * Examples: "invalid_transition", "already_converted", "client_is_lost".
   */
  error_code: string;
  /**
   * Allowed transition targets when the server returns a 409 with
   * an `allowed` array (stage or state machine violation).
   */
  allowed: string[] | undefined;
  /** Raw parsed response body — useful for callers that need extra context. */
  original: unknown;

  constructor({
    message,
    status,
    error_code,
    allowed,
    original,
  }: {
    message: string;
    status: number;
    error_code: string;
    allowed?: string[];
    original: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.error_code = error_code;
    this.allowed = allowed;
    this.original = original;
  }
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  private async _doRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.setToken(null);
        // Only force a redirect when the user is NOT already on /login.
        // Otherwise the auth-context's mount-time getMe() call loops:
        //   /login -> getMe 401 -> location.href = /login -> reload -> repeat.
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          const currentPath = window.location.pathname + window.location.search;
          sessionStorage.setItem("returnTo", currentPath);
          window.location.href = "/login";
        }
      }

      const errorData = await response.json().catch(() => ({
        error: `HTTP ${response.status}: ${response.statusText}`,
      }));

      // Derive human-readable message — keeps backward compat for callers using .message
      let message: string;
      // FastAPI 422 validation error: { "detail": [{msg: "...", ...}, ...] }
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          message =
            errorData.detail
              .map((d: Record<string, string>) => d.msg)
              .filter(Boolean)
              .join(", ") || "Error de validación";
        } else {
          message = String(errorData.detail);
        }
      } else {
        message = String(errorData.error || errorData.message || "Unknown error");
      }

      throw new ApiError({
        message,
        status: response.status,
        error_code: String(errorData.error || errorData.error_code || `HTTP_${response.status}`),
        allowed: Array.isArray(errorData.allowed) ? (errorData.allowed as string[]) : undefined,
        original: errorData,
      });
    }

    if (
      response.status === 204 ||
      response.headers.get("content-length") === "0"
    ) {
      return undefined as T;
    }
    return response.json();
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const method = (options.method || "GET").toUpperCase();

    // Deduplicate concurrent GET requests to the same endpoint
    if (method === "GET") {
      const existing = inflight.get(endpoint);
      if (existing) return existing as Promise<T>;

      const promise = this._doRequest<T>(endpoint, options).finally(() => {
        inflight.delete(endpoint);
      });
      inflight.set(endpoint, promise);
      return promise;
    }

    return this._doRequest<T>(endpoint, options);
  }

  // ===========================================
  // Auth endpoints
  // ===========================================

  async login(
    email: string,
    password: string
  ): Promise<{ access_token: string; token_type: string; expires_at: string; role: string }> {
    const response = await this.request<{
      access_token: string;
      token_type: string;
      expires_at: string;
      role: string;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(response.access_token);
    return response;
  }

  async logout(): Promise<void> {
    try {
      await this.request("/api/auth/logout", { method: "POST" });
    } catch (error) {
      console.warn("Server logout failed:", error);
    }
    this.setToken(null);
  }

  async getMe(): Promise<CurrentUser> {
    return this.request("/api/auth/me");
  }

  // ===========================================
  // Leads endpoints
  // ===========================================

  async listLeads(filters: {
    vertical?: string;
    channel?: string;
    status?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<LeadListResponse> {
    const params = new URLSearchParams();
    if (filters.vertical) params.set("vertical", filters.vertical);
    if (filters.channel) params.set("channel", filters.channel);
    if (filters.status) params.set("status", filters.status);
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));
    if (filters.offset !== undefined) params.set("offset", String(filters.offset));
    const qs = params.toString();
    return this.request(`/api/leads${qs ? `?${qs}` : ""}`);
  }

  async getLead(id: string): Promise<Lead> {
    return this.request(`/api/leads/${id}`);
  }

  async updateLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
    return this.request(`/api/leads/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  }

  async assignLead(id: string, ownerId: string): Promise<Lead> {
    return this.request(`/api/leads/${id}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ owner_id: ownerId }),
    });
  }

  // ===========================================
  // Users endpoints (for assign modal)
  // ===========================================

  async listUsers(): Promise<UserListResponse> {
    // TODO Phase 5: implement GET /api/users when backend adds it
    return Promise.resolve({ items: [], total: 0 });
  }

  // ===========================================
  // Clients endpoints
  // ===========================================

  async getClients(filters: ClientFilters = {}): Promise<ClientListResponse> {
    const params = new URLSearchParams();
    if (filters.stage) params.set("stage", filters.stage);
    if (filters.owner_id) params.set("owner_id", filters.owner_id);
    if (filters.sector) params.set("sector", filters.sector);
    if (filters.q) params.set("q", filters.q);
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));
    if (filters.offset !== undefined) params.set("offset", String(filters.offset));
    const qs = params.toString();
    return this.request(`/api/clients${qs ? `?${qs}` : ""}`);
  }

  async getClient(id: string): Promise<ClientDetailResponse> {
    return this.request(`/api/clients/${id}`);
  }

  async createClient(body: {
    name: string;
    sector?: string;
    size?: string;
    region?: string;
    owner_id?: string;
    mrr_cents?: number;
    stage?: ClientStage;
  }): Promise<ClientRead> {
    return this.request("/api/clients", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async patchClient(id: string, body: ClientUpdate): Promise<ClientRead> {
    return this.request(`/api/clients/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async patchClientStage(id: string, new_stage: ClientStage): Promise<ClientRead> {
    return this.request(`/api/clients/${id}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ stage: new_stage }),
    });
  }

  // ===========================================
  // Contacts endpoints
  // ===========================================

  async getClientContacts(clientId: string): Promise<ContactRead[]> {
    return this.request(`/api/clients/${clientId}/contacts`);
  }

  async createContact(clientId: string, body: ContactCreate): Promise<ContactRead> {
    return this.request(`/api/clients/${clientId}/contacts`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async patchContact(
    clientId: string,
    contactId: string,
    body: ContactUpdate
  ): Promise<ContactRead> {
    return this.request(`/api/clients/${clientId}/contacts/${contactId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async deleteContact(clientId: string, contactId: string): Promise<void> {
    return this.request(`/api/clients/${clientId}/contacts/${contactId}`, {
      method: "DELETE",
    });
  }

  // ===========================================
  // Services endpoints
  // ===========================================

  async getServices(filters: ServiceFilters = {}): Promise<ServiceListResponse> {
    const params = new URLSearchParams();
    if (filters.client_id) params.set("client_id", filters.client_id);
    if (filters.owner_id) params.set("owner_id", filters.owner_id);
    if (filters.state) params.set("state", filters.state);
    if (filters.type) params.set("type", filters.type);
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));
    if (filters.offset !== undefined) params.set("offset", String(filters.offset));
    const qs = params.toString();
    return this.request(`/api/services${qs ? `?${qs}` : ""}`);
  }

  async getService(id: string): Promise<ServiceRead> {
    return this.request(`/api/services/${id}`);
  }

  async createService(clientId: string, body: {
    type: ServiceType;
    title: string;
    owner_id?: string;
    setup_price_cents?: number;
    monthly_cents?: number;
  }): Promise<ServiceRead> {
    return this.request(`/api/clients/${clientId}/services`, {
      method: "POST",
      body: JSON.stringify({ client_id: clientId, ...body }),
    });
  }

  async patchService(id: string, body: ServiceUpdate): Promise<ServiceRead> {
    return this.request(`/api/services/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async patchServiceState(id: string, new_state: ServiceState): Promise<ServiceRead> {
    return this.request(`/api/services/${id}/state`, {
      method: "PATCH",
      body: JSON.stringify({ state: new_state }),
    });
  }

  // ===========================================
  // Milestones endpoints
  // ===========================================

  async getMilestones(serviceId: string): Promise<MilestoneRead[]> {
    return this.request(`/api/services/${serviceId}/milestones`);
  }

  async createMilestone(serviceId: string, body: MilestoneCreate): Promise<MilestoneRead> {
    return this.request(`/api/services/${serviceId}/milestones`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async patchMilestone(
    serviceId: string,
    n: number,
    body: MilestoneUpdate
  ): Promise<MilestoneRead> {
    return this.request(`/api/services/${serviceId}/milestones/${n}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  async deleteMilestone(serviceId: string, n: number): Promise<void> {
    return this.request(`/api/services/${serviceId}/milestones/${n}`, {
      method: "DELETE",
    });
  }

  // ===========================================
  // Lead conversion
  // ===========================================

  async convertLead(leadId: string, body: ConvertLeadBody = {}): Promise<ClientRead> {
    return this.request(`/api/leads/${leadId}/convert`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  // ===========================================
  // Activity endpoint
  // ===========================================

  async getActivity(params: ActivityFilters = {}): Promise<ActivityLogListResponse> {
    const qs = new URLSearchParams();
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    if (params.client_id) qs.set("client_id", params.client_id);
    const qStr = qs.toString();
    return this.request(`/api/activity${qStr ? `?${qStr}` : ""}`);
  }

  // ===========================================
  // Client Portal — /api/me/* namespace
  // ===========================================

  me = {
    /** GET /api/me/client — own client record */
    getMyClient: (): Promise<ClientRead> =>
      this.request("/api/me/client"),

    /** GET /api/me/services — all services for own client */
    getMyServices: (): Promise<ServiceListResponse> =>
      this.request("/api/me/services"),

    /** GET /api/me/services/{id} — single service (includes diagnostic_json) */
    getMyService: (id: string): Promise<ServiceRead> =>
      this.request(`/api/me/services/${id}`),

    /** GET /api/me/services/{id}/diagnostic */
    getMyDiagnostic: (serviceId: string): Promise<Diagnostic | null> =>
      this.request(`/api/me/services/${serviceId}/diagnostic`),

    /** GET /api/me/contacts */
    getMyContacts: (): Promise<ContactRead[]> =>
      this.request("/api/me/contacts"),

    /** GET /api/me/activity */
    getMyActivity: (params: ActivityFilters = {}): Promise<ActivityLogListResponse> => {
      const qs = new URLSearchParams();
      if (params.limit !== undefined) qs.set("limit", String(params.limit));
      if (params.offset !== undefined) qs.set("offset", String(params.offset));
      const qStr = qs.toString();
      return this.request(`/api/me/activity${qStr ? `?${qStr}` : ""}`);
    },

    /** GET /api/me/messages?since=<iso> */
    getMyMessages: (since?: string): Promise<MessageListResponse> => {
      const qs = since ? `?since=${encodeURIComponent(since)}` : "";
      return this.request(`/api/me/messages${qs}`);
    },

    /** POST /api/me/messages */
    postMyMessage: (body: MessageCreate): Promise<Message> =>
      this.request("/api/me/messages", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    /** GET /api/me/tickets?status=<status> */
    getMyTickets: (status?: TicketStatus): Promise<TicketListResponse> => {
      const qs = status ? `?status=${status}` : "";
      return this.request(`/api/me/tickets${qs}`);
    },

    /** POST /api/me/tickets */
    postMyTicket: (body: TicketCreate): Promise<Ticket> =>
      this.request("/api/me/tickets", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    /** PATCH /api/me/tickets/{id} */
    patchMyTicket: (id: string, body: TicketPatch): Promise<Ticket> =>
      this.request(`/api/me/tickets/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  };

  // ===========================================
  // Internal client portal helpers (admin/consultor)
  // ===========================================

  /** GET /api/clients/{id}/messages */
  async getClientMessages(clientId: string): Promise<MessageListResponse> {
    return this.request(`/api/clients/${clientId}/messages`);
  }

  /** POST /api/clients/{id}/messages */
  async postClientMessage(clientId: string, body: MessageCreate): Promise<Message> {
    return this.request(`/api/clients/${clientId}/messages`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /** GET /api/clients/{id}/tickets */
  async getClientTickets(clientId: string, status?: TicketStatus): Promise<TicketListResponse> {
    const qs = status ? `?status=${status}` : "";
    return this.request(`/api/clients/${clientId}/tickets${qs}`);
  }

  /** PATCH /api/tickets/{id} (internal admin update) */
  async patchTicket(id: string, body: TicketPatch): Promise<Ticket> {
    return this.request(`/api/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }
}

const api = new ApiClient(API_BASE_URL);
export default api;
