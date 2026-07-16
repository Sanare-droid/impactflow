export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "ImpactFlow AI";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_URL}/api/v1`;

export type UserBrief = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  primary_organization_id?: string | null;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  organization_type: string;
  country_code?: string | null;
  timezone: string;
  locale: string;
  logo_url?: string | null;
  website?: string | null;
  email?: string | null;
  is_active: boolean;
  is_verified: boolean;
  settings: Record<string, unknown>;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  mfa_required: boolean;
  user: UserBrief;
};

export type DashboardStats = {
  users_count: number;
  active_memberships: number;
  roles_count: number;
  recent_audit_events: number;
  organization: Organization;
  programs_count: number;
  projects_count: number;
  activities_count: number;
  tasks_count: number;
  open_tasks_count: number;
  donors_count: number;
  grants_count: number;
  active_grants_count: number;
  budgets_count: number;
  grants_awarded_total: string;
  grants_received_total: string;
  expenses_total: string;
  theories_of_change_count: number;
  logframes_count: number;
  indicators_count: number;
  active_indicators_count: number;
  monitoring_results_count: number;
  evaluations_count: number;
  communities_count: number;
  households_count: number;
  beneficiaries_count: number;
  active_beneficiaries_count: number;
  beneficiary_memberships_count: number;
  reports_count: number;
  published_reports_count: number;
  saved_dashboards_count: number;
  map_layers_count: number;
  map_features_count: number;
  evidence_count: number;
  verified_evidence_count: number;
  ai_conversations_count: number;
  ai_predictions_count: number;
  open_predictions_count: number;
  ai_narratives_count: number;
  knowledge_documents_count: number;
  marketplace_installs_count: number;
  integrations_count: number;
  api_keys_count: number;
  branding_enabled_count: number;
};

export type Role = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_system: boolean;
  is_default: boolean;
  permissions: string[];
};

export type Paginated<T> = {
  items: T[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
};

export type Program = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  manager_id?: string | null;
  goal?: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: string;
  organization_id: string;
  program_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  country_code?: string | null;
  location?: string | null;
  manager_id?: string | null;
  priority: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type ActivityItem = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  sort_order: number;
  owner_id?: string | null;
  location?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkPlan = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  description?: string | null;
  status: string;
  period_start?: string | null;
  period_end?: string | null;
  fiscal_year?: number | null;
  period_label?: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskItem = {
  id: string;
  organization_id: string;
  project_id: string;
  activity_id?: string | null;
  work_plan_id?: string | null;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  assignee_id?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type Donor = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  donor_type: string;
  status: string;
  country_code?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  website?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Grant = {
  id: string;
  organization_id: string;
  donor_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  currency: string;
  amount_awarded: number | string;
  amount_received: number | string;
  start_date?: string | null;
  end_date?: string | null;
  agreement_reference?: string | null;
  created_at: string;
  updated_at: string;
};

export type BudgetLine = {
  id: string;
  budget_id: string;
  category: string;
  code?: string | null;
  description?: string | null;
  amount: number | string;
  sort_order: number;
};

export type Budget = {
  id: string;
  organization_id: string;
  grant_id?: string | null;
  project_id?: string | null;
  program_id?: string | null;
  name: string;
  fiscal_year?: number | null;
  currency: string;
  status: string;
  total_amount: number | string;
  notes?: string | null;
  lines?: BudgetLine[];
  created_at: string;
  updated_at: string;
};

export type FinanceTxn = {
  id: string;
  organization_id: string;
  grant_id?: string | null;
  project_id?: string | null;
  budget_id?: string | null;
  transaction_type: string;
  status: string;
  amount: number | string;
  currency: string;
  transaction_date: string;
  description?: string | null;
  reference?: string | null;
  category?: string | null;
  created_at: string;
  updated_at: string;
};

export type TheoryOfChange = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  status: string;
  goal_statement?: string | null;
  problem_statement?: string | null;
  assumptions?: string | null;
  success_criteria?: string | null;
  pathways?: unknown[];
  created_at: string;
  updated_at: string;
};

export type LogframeResult = {
  id: string;
  logframe_id: string;
  parent_id?: string | null;
  level: string;
  code?: string | null;
  statement: string;
  assumptions?: string | null;
  means_of_verification?: string | null;
  sort_order: number;
};

export type Logframe = {
  id: string;
  organization_id: string;
  theory_of_change_id?: string | null;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  results?: LogframeResult[];
  created_at: string;
  updated_at: string;
};

export type IndicatorTarget = {
  id: string;
  indicator_id: string;
  period_label: string;
  start_date?: string | null;
  end_date?: string | null;
  target_value: number | string;
  notes?: string | null;
  status: string;
};

export type Indicator = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  logframe_result_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  level: string;
  measure_type: string;
  unit?: string | null;
  direction: string;
  collection_method?: string | null;
  frequency?: string | null;
  baseline_value?: number | string | null;
  baseline_date?: string | null;
  status: string;
  targets?: IndicatorTarget[];
  created_at: string;
  updated_at: string;
};

export type MonitoringResult = {
  id: string;
  organization_id: string;
  indicator_id: string;
  target_id?: string | null;
  project_id?: string | null;
  reporting_date: string;
  period_start?: string | null;
  period_end?: string | null;
  actual_value?: number | string | null;
  qualitative_value?: string | null;
  status: string;
  data_source?: string | null;
  location_label?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Evaluation = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  evaluation_type: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  evaluator_name?: string | null;
  objectives?: string | null;
  methodology?: string | null;
  key_findings?: string | null;
  recommendations?: string | null;
  lessons_learned?: string | null;
  created_at: string;
  updated_at: string;
};

export type Community = {
  id: string;
  organization_id: string;
  parent_id?: string | null;
  name: string;
  code: string;
  community_type: string;
  status: string;
  country_code?: string | null;
  region?: string | null;
  district?: string | null;
  population_estimate?: number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Household = {
  id: string;
  organization_id: string;
  community_id?: string | null;
  name: string;
  code: string;
  status: string;
  address?: string | null;
  household_size?: number | null;
  poverty_status?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type BeneficiaryMembership = {
  id: string;
  beneficiary_id: string;
  program_id?: string | null;
  project_id?: string | null;
  activity_id?: string | null;
  membership_role: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
};

export type Beneficiary = {
  id: string;
  organization_id: string;
  household_id?: string | null;
  community_id?: string | null;
  code: string;
  first_name: string;
  last_name: string;
  middle_name?: string | null;
  sex?: string | null;
  date_of_birth?: string | null;
  national_id?: string | null;
  phone?: string | null;
  email?: string | null;
  status: string;
  registration_date?: string | null;
  consent_data_use: boolean;
  is_household_head: boolean;
  memberships?: BeneficiaryMembership[];
  created_at: string;
  updated_at: string;
};

export type Report = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  grant_id?: string | null;
  name: string;
  code: string;
  report_type: string;
  status: string;
  period_start?: string | null;
  period_end?: string | null;
  summary?: string | null;
  content?: string | null;
  sections?: unknown[];
  created_at: string;
  updated_at: string;
};

export type SavedDashboard = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  is_default: boolean;
  layout?: Record<string, unknown>;
  widgets?: unknown[];
  filters?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MapFeature = {
  id: string;
  layer_id: string;
  name: string;
  feature_type: string;
  latitude?: number | string | null;
  longitude?: number | string | null;
  properties?: Record<string, unknown>;
  sort_order: number;
};

export type MapLayer = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  layer_type: string;
  status: string;
  description?: string | null;
  features?: MapFeature[];
  created_at: string;
  updated_at: string;
};

export type EvidenceItem = {
  id: string;
  organization_id: string;
  title: string;
  code: string;
  evidence_type: string;
  status: string;
  description?: string | null;
  collected_on?: string | null;
  source?: string | null;
  file_url?: string | null;
  tags?: unknown[];
  created_at: string;
  updated_at: string;
};

export type AnalyticsOverview = {
  delivery: Record<string, unknown>;
  finance: Record<string, unknown>;
  meal: Record<string, unknown>;
  field: Record<string, unknown>;
  insights: Record<string, unknown>;
  reports_by_status: Record<string, number>;
  evidence_by_type: Record<string, number>;
};

export type AiConversation = {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  status: string;
  context?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AiMessage = {
  id: string;
  organization_id: string;
  conversation_id: string;
  role: string;
  content: string;
  model?: string | null;
  provider: string;
  token_count?: number | null;
  created_at: string;
  updated_at: string;
};

export type AiConversationDetail = AiConversation & {
  messages: AiMessage[];
};

export type AiPrediction = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  prediction_type: string;
  title: string;
  summary: string;
  severity: string;
  score: string | number;
  status: string;
  recommendations: string[];
  provider: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
};

export type AiNarrative = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  narrative_type: string;
  status: string;
  prompt?: string | null;
  content: string;
  provider: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocument = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  category: string;
  status: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  tags?: unknown[];
  created_at: string;
  updated_at: string;
};

export type MarketplaceApp = {
  id: string;
  name: string;
  code: string;
  category: string;
  summary?: string | null;
  description?: string | null;
  publisher: string;
  pricing_tier: string;
  status: string;
  is_featured: boolean;
  icon_key?: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketplaceInstallation = {
  id: string;
  organization_id: string;
  app_id: string;
  status: string;
  config?: Record<string, unknown>;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type OrgApiKey = {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  status: string;
  scopes: string[];
  created_at: string;
  updated_at: string;
};

export type OrgApiKeyCreated = OrgApiKey & { secret: string };

export type IntegrationConnection = {
  id: string;
  organization_id: string;
  name: string;
  provider: string;
  status: string;
  direction: string;
  endpoint_url?: string | null;
  secret_hint?: string | null;
  events?: string[];
  last_sync_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type OrgBranding = {
  id: string;
  organization_id: string;
  product_name?: string | null;
  tagline?: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color?: string | null;
  logo_url?: string | null;
  favicon_url?: string | null;
  custom_domain?: string | null;
  support_email?: string | null;
  support_url?: string | null;
  hide_powered_by: boolean;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
};

type ApiError = {
  message?: string;
  code?: string;
  details?: Record<string, unknown>;
};

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private organizationId: string | null = null;

  hydrateFromStorage() {
    if (typeof window === "undefined") return;
    this.accessToken = localStorage.getItem("if_access_token");
    this.refreshToken = localStorage.getItem("if_refresh_token");
    this.organizationId = localStorage.getItem("if_organization_id");
  }

  setSession(tokens: {
    access_token: string;
    refresh_token: string;
    organization_id?: string | null;
  }) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (tokens.organization_id) {
      this.organizationId = tokens.organization_id;
    }
    if (typeof window !== "undefined") {
      localStorage.setItem("if_access_token", tokens.access_token);
      localStorage.setItem("if_refresh_token", tokens.refresh_token);
      if (tokens.organization_id) {
        localStorage.setItem("if_organization_id", tokens.organization_id);
      }
    }
  }

  clearSession() {
    this.accessToken = null;
    this.refreshToken = null;
    this.organizationId = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("if_access_token");
      localStorage.removeItem("if_refresh_token");
      localStorage.removeItem("if_organization_id");
      localStorage.removeItem("if_user");
    }
  }

  get hasSession() {
    return Boolean(this.accessToken);
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true,
  ): Promise<T> {
    this.hydrateFromStorage();
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (this.accessToken) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }
    if (this.organizationId) {
      headers.set("X-Organization-Id", this.organizationId);
    }

    const res = await fetch(`${API_V1}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && retry && this.refreshToken) {
      const refreshed = await this.refresh();
      if (refreshed) {
        return this.request<T>(path, options, false);
      }
      this.clearSession();
    }

    if (!res.ok) {
      let error: ApiError = { message: res.statusText };
      try {
        error = await res.json();
      } catch {
        /* ignore */
      }
      throw new Error(error.message || "Request failed");
    }

    if (res.status === 204) {
      return undefined as T;
    }
    return res.json() as Promise<T>;
  }

  async refresh(): Promise<boolean> {
    if (!this.refreshToken) return false;
    try {
      const data = await fetch(`${API_V1}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      }).then(async (res) => {
        if (!res.ok) return null;
        return res.json() as Promise<TokenResponse>;
      });
      if (!data?.access_token) return false;
      this.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        organization_id: data.user.primary_organization_id,
      });
      return true;
    } catch {
      return false;
    }
  }

  register(body: Record<string, unknown>) {
    return this.request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  login(body: Record<string, unknown>) {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  logout() {
    const token = this.refreshToken;
    this.clearSession();
    if (!token) return Promise.resolve();
    return this.request("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: token }),
    }).catch(() => undefined);
  }

  me() {
    return this.request<UserBrief>("/auth/me");
  }

  currentOrganization() {
    return this.request<Organization>("/organizations/current");
  }

  dashboardStats() {
    return this.request<DashboardStats>("/dashboard/stats");
  }

  roles() {
    return this.request<Role[]>("/roles");
  }

  permissions() {
    return this.request<{ roles: string[]; permissions: string[] }>(
      "/me/permissions",
    );
  }

  listPrograms(params: { page?: number; search?: string; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<Program>>(`/programs${qs ? `?${qs}` : ""}`);
  }

  createProgram(body: Record<string, unknown>) {
    return this.request<Program>("/programs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getProgram(id: string) {
    return this.request<Program>(`/programs/${id}`);
  }

  updateProgram(id: string, body: Record<string, unknown>) {
    return this.request<Program>(`/programs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  deleteProgram(id: string) {
    return this.request<{ message: string }>(`/programs/${id}`, {
      method: "DELETE",
    });
  }

  listProjects(
    params: {
      page?: number;
      program_id?: string;
      search?: string;
      status?: string;
    } = {},
  ) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<Project>>(`/projects${qs ? `?${qs}` : ""}`);
  }

  createProject(body: Record<string, unknown>) {
    return this.request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getProject(id: string) {
    return this.request<Project>(`/projects/${id}`);
  }

  updateProject(id: string, body: Record<string, unknown>) {
    return this.request<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  deleteProject(id: string) {
    return this.request<{ message: string }>(`/projects/${id}`, {
      method: "DELETE",
    });
  }

  listActivities(projectId: string) {
    return this.request<Paginated<ActivityItem>>(
      `/activities?project_id=${projectId}&page_size=100`,
    );
  }

  createActivity(body: Record<string, unknown>) {
    return this.request<ActivityItem>("/activities", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateActivity(id: string, body: Record<string, unknown>) {
    return this.request<ActivityItem>(`/activities/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listWorkPlans(projectId: string) {
    return this.request<Paginated<WorkPlan>>(
      `/work-plans?project_id=${projectId}&page_size=50`,
    );
  }

  createWorkPlan(body: Record<string, unknown>) {
    return this.request<WorkPlan>("/work-plans", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTasks(params: { project_id?: string; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.project_id) q.set("project_id", params.project_id);
    if (params.status) q.set("status", params.status);
    q.set("page_size", "100");
    return this.request<Paginated<TaskItem>>(`/tasks?${q.toString()}`);
  }

  createTask(body: Record<string, unknown>) {
    return this.request<TaskItem>("/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateTask(id: string, body: Record<string, unknown>) {
    return this.request<TaskItem>(`/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listDonors(params: { search?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Donor>>(`/donors?${q}`);
  }

  createDonor(body: Record<string, unknown>) {
    return this.request<Donor>("/donors", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listGrants(params: { donor_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.donor_id) q.set("donor_id", params.donor_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Grant>>(`/grants?${q}`);
  }

  createGrant(body: Record<string, unknown>) {
    return this.request<Grant>("/grants", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateGrant(id: string, body: Record<string, unknown>) {
    return this.request<Grant>(`/grants/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listBudgets(params: { grant_id?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.grant_id) q.set("grant_id", params.grant_id);
    return this.request<Paginated<Budget>>(`/budgets?${q}`);
  }

  createBudget(body: Record<string, unknown>) {
    return this.request<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getBudget(id: string) {
    return this.request<Budget>(`/budgets/${id}`);
  }

  addBudgetLine(budgetId: string, body: Record<string, unknown>) {
    return this.request<BudgetLine>(`/budgets/${budgetId}/lines`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTransactions(params: { grant_id?: string; transaction_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.grant_id) q.set("grant_id", params.grant_id);
    if (params.transaction_type) q.set("transaction_type", params.transaction_type);
    return this.request<Paginated<FinanceTxn>>(`/finance/transactions?${q}`);
  }

  createTransaction(body: Record<string, unknown>) {
    return this.request<FinanceTxn>("/finance/transactions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTheoriesOfChange(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<TheoryOfChange>>(`/theories-of-change?${q}`);
  }

  createTheoryOfChange(body: Record<string, unknown>) {
    return this.request<TheoryOfChange>("/theories-of-change", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listLogframes(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Logframe>>(`/logframes?${q}`);
  }

  createLogframe(body: Record<string, unknown>) {
    return this.request<Logframe>("/logframes", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addLogframeResult(logframeId: string, body: Record<string, unknown>) {
    return this.request<LogframeResult>(`/logframes/${logframeId}/results`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listIndicators(params: { status?: string; level?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.level) q.set("level", params.level);
    return this.request<Paginated<Indicator>>(`/indicators?${q}`);
  }

  createIndicator(body: Record<string, unknown>) {
    return this.request<Indicator>("/indicators", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addIndicatorTarget(indicatorId: string, body: Record<string, unknown>) {
    return this.request<IndicatorTarget>(`/indicators/${indicatorId}/targets`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMonitoringResults(params: { indicator_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.indicator_id) q.set("indicator_id", params.indicator_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<MonitoringResult>>(`/monitoring-results?${q}`);
  }

  createMonitoringResult(body: Record<string, unknown>) {
    return this.request<MonitoringResult>("/monitoring-results", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateMonitoringResult(id: string, body: Record<string, unknown>) {
    return this.request<MonitoringResult>(`/monitoring-results/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listEvaluations(params: { status?: string; evaluation_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.evaluation_type) q.set("evaluation_type", params.evaluation_type);
    return this.request<Paginated<Evaluation>>(`/evaluations?${q}`);
  }

  createEvaluation(body: Record<string, unknown>) {
    return this.request<Evaluation>("/evaluations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listCommunities(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Community>>(`/communities?${q}`);
  }

  createCommunity(body: Record<string, unknown>) {
    return this.request<Community>("/communities", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listHouseholds(params: { community_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.community_id) q.set("community_id", params.community_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Household>>(`/households?${q}`);
  }

  createHousehold(body: Record<string, unknown>) {
    return this.request<Household>("/households", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listBeneficiaries(params: {
    household_id?: string;
    community_id?: string;
    status?: string;
    search?: string;
  } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.household_id) q.set("household_id", params.household_id);
    if (params.community_id) q.set("community_id", params.community_id);
    if (params.status) q.set("status", params.status);
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<Beneficiary>>(`/beneficiaries?${q}`);
  }

  createBeneficiary(body: Record<string, unknown>) {
    return this.request<Beneficiary>("/beneficiaries", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addBeneficiaryMembership(beneficiaryId: string, body: Record<string, unknown>) {
    return this.request<BeneficiaryMembership>(
      `/beneficiaries/${beneficiaryId}/memberships`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
  }

  listBeneficiaryMemberships(params: { beneficiary_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.beneficiary_id) q.set("beneficiary_id", params.beneficiary_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<BeneficiaryMembership>>(`/beneficiary-memberships?${q}`);
  }

  analyticsOverview() {
    return this.request<AnalyticsOverview>("/analytics/overview");
  }

  listReports(params: { status?: string; report_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.report_type) q.set("report_type", params.report_type);
    return this.request<Paginated<Report>>(`/reports?${q}`);
  }

  createReport(body: Record<string, unknown>) {
    return this.request<Report>("/reports", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listSavedDashboards() {
    return this.request<Paginated<SavedDashboard>>("/saved-dashboards?page_size=100");
  }

  createSavedDashboard(body: Record<string, unknown>) {
    return this.request<SavedDashboard>("/saved-dashboards", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMapLayers() {
    return this.request<Paginated<MapLayer>>("/map-layers?page_size=100");
  }

  createMapLayer(body: Record<string, unknown>) {
    return this.request<MapLayer>("/map-layers", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addMapFeature(layerId: string, body: Record<string, unknown>) {
    return this.request<MapFeature>(`/map-layers/${layerId}/features`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listEvidence(params: { status?: string; evidence_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.evidence_type) q.set("evidence_type", params.evidence_type);
    return this.request<Paginated<EvidenceItem>>(`/evidence?${q}`);
  }

  createEvidence(body: Record<string, unknown>) {
    return this.request<EvidenceItem>("/evidence", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listAiConversations() {
    return this.request<Paginated<AiConversation>>("/ai/conversations?page_size=50");
  }

  createAiConversation(body: Record<string, unknown> = {}) {
    return this.request<AiConversation>("/ai/conversations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getAiConversation(id: string) {
    return this.request<AiConversationDetail>(`/ai/conversations/${id}`);
  }

  sendAiMessage(conversationId: string, content: string) {
    return this.request<AiConversationDetail>(
      `/ai/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      }
    );
  }

  listAiPredictions(params: { status?: string; severity?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.severity) q.set("severity", params.severity);
    return this.request<Paginated<AiPrediction>>(`/ai/predictions?${q}`);
  }

  generateAiPrediction(body: Record<string, unknown> = {}) {
    return this.request<AiPrediction>("/ai/predictions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateAiPrediction(id: string, body: Record<string, unknown>) {
    return this.request<AiPrediction>(`/ai/predictions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listAiNarratives() {
    return this.request<Paginated<AiNarrative>>("/ai/narratives?page_size=100");
  }

  generateAiNarrative(body: Record<string, unknown>) {
    return this.request<AiNarrative>("/ai/narratives", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listKnowledge(params: { search?: string; category?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.search) q.set("search", params.search);
    if (params.category) q.set("category", params.category);
    return this.request<Paginated<KnowledgeDocument>>(`/knowledge?${q}`);
  }

  createKnowledge(body: Record<string, unknown>) {
    return this.request<KnowledgeDocument>("/knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMarketplaceApps(params: { category?: string; search?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.category) q.set("category", params.category);
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<MarketplaceApp>>(`/marketplace/apps?${q}`);
  }

  listMarketplaceInstallations() {
    return this.request<Paginated<MarketplaceInstallation>>(
      "/marketplace/installations?page_size=100"
    );
  }

  installMarketplaceApp(body: Record<string, unknown>) {
    return this.request<MarketplaceInstallation>("/marketplace/installations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateMarketplaceInstallation(id: string, body: Record<string, unknown>) {
    return this.request<MarketplaceInstallation>(`/marketplace/installations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listApiKeys() {
    return this.request<Paginated<OrgApiKey>>("/api-keys?page_size=100");
  }

  createApiKey(body: Record<string, unknown>) {
    return this.request<OrgApiKeyCreated>("/api-keys", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  revokeApiKey(id: string) {
    return this.request<OrgApiKey>(`/api-keys/${id}/revoke`, { method: "POST" });
  }

  listIntegrations() {
    return this.request<Paginated<IntegrationConnection>>("/integrations?page_size=100");
  }

  createIntegration(body: Record<string, unknown>) {
    return this.request<IntegrationConnection>("/integrations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  testIntegration(id: string) {
    return this.request<IntegrationConnection>(`/integrations/${id}/test`, {
      method: "POST",
    });
  }

  getBranding() {
    return this.request<OrgBranding>("/branding");
  }

  updateBranding(body: Record<string, unknown>) {
    return this.request<OrgBranding>("/branding", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }
}

export const api = new ApiClient();
