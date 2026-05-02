/**
 * Zanovix CRM Admin Panel - Type definitions
 */

// ===========================================
// Auth Types
// ===========================================

export type UserRole = "admin" | "consultor" | "comercial";

// Keep AdminRole as alias for backward compat with auth-context
export type AdminRole = UserRole;

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string | null;
  role: UserRole;
  is_active: boolean;
}

// ===========================================
// Lead Types
// ===========================================

export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "disqualified"
  | "converted";

export type LeadVertical = "clinicas_dentales" | "general";

export type LeadChannel =
  | "email_marketing"
  | "cold_calling"
  | "networking"
  | "referral"
  | "web_form"
  | "other";

export interface Lead {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  email: string;
  phone: string | null;
  company: string | null;
  vertical: LeadVertical;
  channel: LeadChannel;
  source_url: string | null;
  notes: string | null;
  status: LeadStatus;
  owner_id: string | null;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

// ===========================================
// User (assignable owner) Types
// ===========================================

export interface AssignableUser {
  id: string;
  display_name: string | null;
  email: string;
  role: UserRole;
}

export interface UserListResponse {
  items: AssignableUser[];
  total: number;
}

// ===========================================
// Status machine (mirrored from backend)
// ===========================================

export const VALID_TRANSITIONS: Record<LeadStatus, LeadStatus[]> = {
  new: ["contacted", "disqualified"],
  contacted: ["qualified", "disqualified"],
  qualified: ["converted", "disqualified"],
  disqualified: [],
  converted: [],
};
