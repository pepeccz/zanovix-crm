/**
 * Zanovix CRM Admin Panel - Type definitions
 */

// ===========================================
// Auth Types
// ===========================================

export type UserRole = "admin" | "consultor" | "comercial" | "client_user";

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

// ===========================================
// CRM — Union / Enum Types
// ===========================================

export type ClientStage =
  | "lead"
  | "discovery_scheduled"
  | "discovery_done"
  | "proposal_sent"
  | "active"
  | "lost";

export type ServiceType = "assessment" | "development" | "formation";

export type ServiceState =
  | "scoping"
  | "running"
  | "delivered"
  | "won"
  | "lost";

export type ActivityKind =
  | "stage_change"
  | "contact_added"
  | "contact_updated"
  | "service_started"
  | "service_state_change"
  | "milestone_completed"
  | "lead_converted"
  | "note";

// ===========================================
// CRM — Core Interfaces (mirror Pydantic exactly)
// ===========================================

export interface ClientRead {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  sector: string | null;
  size: string | null;
  region: string | null;
  owner_id: string | null;
  stage: ClientStage;
  entered_at: string;
  mrr_cents: number | null;
  lifetime_value_cents: number | null;
}

export interface ContactRead {
  id: string;
  created_at: string;
  updated_at: string;
  client_id: string;
  name: string;
  role: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
}

export interface ServiceStub {
  id: string;
  title: string;
  type: ServiceType;
  state: ServiceState;
  progress_pct: number | null;
  owner_id: string | null;
}

export interface MilestoneRead {
  id: string;
  service_id: string;
  n: number;
  title: string;
  due_date: string | null;
  completed_at: string | null;
}

export interface ServiceRead {
  id: string;
  created_at: string;
  updated_at: string;
  client_id: string;
  owner_id: string | null;
  type: ServiceType;
  title: string;
  state: ServiceState;
  progress_pct: number | null;
  started_at: string | null;
  ended_at: string | null;
  setup_price_cents: number | null;
  monthly_cents: number | null;
  score_int: number | null;
  milestones: MilestoneRead[];
  diagnostic_json: Diagnostic | null;
}

export interface ActivityLogRead {
  id: string;
  created_at: string;
  client_id: string;
  kind: ActivityKind;
  actor_user_id: string | null;
  body: string;
}

// ===========================================
// CRM — Detail / Nested Response Types
// ===========================================

/**
 * Returned by GET /api/clients/{id}.
 * ClientDetailResponse duplicates all ClientRead fields plus nests
 * contacts, services (stubs), and last 20 activity entries.
 */
export interface ClientDetailResponse {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  sector: string | null;
  size: string | null;
  region: string | null;
  owner_id: string | null;
  stage: ClientStage;
  entered_at: string;
  mrr_cents: number | null;
  lifetime_value_cents: number | null;
  contacts: ContactRead[];
  services: ServiceStub[];
  recent_activity: ActivityLogRead[];
}

// ===========================================
// CRM — Filter / Request Types
// ===========================================

export interface ClientFilters {
  stage?: ClientStage;
  owner_id?: string;
  sector?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface ClientUpdate {
  name?: string;
  sector?: string;
  size?: string;
  region?: string;
  owner_id?: string;
  mrr_cents?: number;
  lifetime_value_cents?: number;
}

export interface ServiceFilters {
  client_id?: string;
  type?: ServiceType;
  state?: ServiceState;
  owner_id?: string;
  limit?: number;
  offset?: number;
}

export interface ServiceUpdate {
  title?: string;
  owner_id?: string;
  progress_pct?: number;
  score_int?: number;
  setup_price_cents?: number;
  monthly_cents?: number;
}

export interface MilestoneCreate {
  n: number;
  title: string;
  due_date?: string;
}

export interface MilestoneUpdate {
  title?: string;
  due_date?: string | null;
  completed_at?: string | null;
}

export interface ContactCreate {
  client_id: string;
  name: string;
  role?: string;
  email?: string;
  phone?: string;
  is_primary?: boolean;
}

export interface ContactUpdate {
  name?: string;
  role?: string;
  email?: string;
  phone?: string;
  is_primary?: boolean;
}

export interface ConvertLeadBody {
  name?: string;
  sector?: string;
  size?: string;
  region?: string;
  owner_id?: string;
  mrr_cents?: number;
  stage?: ClientStage;
}

export interface ActivityFilters {
  limit?: number;
  offset?: number;
  client_id?: string;
}

// ===========================================
// CRM — List Response Types
// ===========================================

export interface ClientListResponse {
  items: ClientRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServiceListResponse {
  items: ServiceRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActivityLogListResponse {
  items: ActivityLogRead[];
  total: number;
  limit: number;
  offset: number;
}

// ===========================================
// CRM — State Machine Transition Maps
// (mirrored from backend service layer)
// ===========================================

export const VALID_CLIENT_STAGE_TRANSITIONS: Record<ClientStage, ClientStage[]> = {
  lead: ["discovery_scheduled", "lost"],
  discovery_scheduled: ["discovery_done", "lost"],
  discovery_done: ["proposal_sent", "lost"],
  proposal_sent: ["active", "lost"],
  active: ["lost"],
  lost: [],
};

export const VALID_SERVICE_STATE_TRANSITIONS: Record<ServiceState, ServiceState[]> = {
  scoping: ["running", "lost"],
  running: ["delivered", "lost"],
  delivered: ["won", "lost"],
  won: [],
  lost: [],
};

// ===========================================
// Client Portal — Tickets
// ===========================================

export type TicketStatus = "pending" | "in_progress" | "closed";
export type TicketPriority = "high" | "medium" | "low";

export interface Ticket {
  id: string;
  client_id: string;
  service_id: string | null;
  title: string;
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
}

export interface TicketCreate {
  title: string;
  priority?: TicketPriority;
  service_id?: string;
}

export interface TicketPatch {
  title?: string;
  priority?: TicketPriority;
  status?: TicketStatus;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  limit: number;
  offset: number;
}

// ===========================================
// Client Portal — Messages
// ===========================================

export interface Message {
  id: string;
  client_id: string;
  sender_user_id: string | null;
  sender_contact_id: string | null;
  body: string;
  created_at: string;
}

export interface MessageCreate {
  body: string;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
}

// ===========================================
// Client Portal — Diagnostic
// ===========================================

export interface DiagnosticDimensions {
  data: number;
  processes: number;
  team: number;
  infrastructure: number;
  compliance: number;
  leadership: number;
}

export interface DiagnosticPlanItem {
  title: string;
  status: "go" | "wait" | "skip";
  body: string;
}

export interface Diagnostic {
  dimensions: DiagnosticDimensions;
  plan: DiagnosticPlanItem[];
  summary: string;
}
