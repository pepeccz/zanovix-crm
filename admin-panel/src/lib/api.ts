/**
 * API Client for Zanovix CRM Admin Panel
 * Handles all HTTP requests to FastAPI backend
 */

import type { CurrentUser, Lead, LeadListResponse, LeadStatus, UserListResponse } from "./types";

// Usa URL relativa - Next.js rewrites hace proxy al backend
const API_BASE_URL = "";

/** In-flight GET request deduplication map (module-scoped, lightweight) */
const inflight = new Map<string, Promise<unknown>>();

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
        if (typeof window !== "undefined") {
          const currentPath = window.location.pathname + window.location.search;
          if (currentPath !== "/login") {
            sessionStorage.setItem("returnTo", currentPath);
          }
          window.location.href = "/login";
        }
      }

      const errorData = await response.json().catch(() => ({
        error: `HTTP ${response.status}: ${response.statusText}`,
      }));
      // Handle FastAPI 422 validation error format: { "detail": [...] }
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          const msgs = errorData.detail
            .map((d: Record<string, string>) => d.msg)
            .filter(Boolean)
            .join(", ");
          throw new Error(msgs || "Error de validación");
        }
        throw new Error(String(errorData.detail));
      }
      throw new Error(errorData.error || "Unknown error");
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
    username: string,
    password: string
  ): Promise<{ access_token: string; token_type: string; expires_in: number }> {
    const response = await this.request<{
      access_token: string;
      token_type: string;
      expires_in: number;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
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
}

const api = new ApiClient(API_BASE_URL);
export default api;
