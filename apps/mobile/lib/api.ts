/**
 * Field app API client — online calls + auth refresh for offline sync.
 * Set EXPO_PUBLIC_API_URL to your machine LAN IP for device testing.
 */
import * as SecureStore from "expo-secure-store";
import { ACCESS_KEY, ORG_KEY, REFRESH_KEY } from "@/lib/sessionKeys";

const API_BASE =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";
const API_V1 = `${API_BASE}/api/v1`;

export type Tokens = {
  access_token: string;
  refresh_token: string;
  mfa_required?: boolean;
  user?: {
    first_name?: string;
    primary_organization_id?: string | null;
  };
};

export type Beneficiary = {
  id: string;
  organization_id?: string;
  code: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  status: string;
  household_id?: string | null;
  community_id?: string | null;
  updated_at?: string;
};

export type Community = {
  id: string;
  organization_id?: string;
  name: string;
  code: string;
  community_type?: string;
  status: string;
  updated_at?: string;
};

export type Household = {
  id: string;
  organization_id?: string;
  name: string;
  code: string;
  community_id?: string | null;
  status: string;
  updated_at?: string;
};

export type SurveyFieldOption = { value: string; label: string };

export type SurveyField = {
  id: string;
  type: string;
  label: string;
  required?: boolean;
  options?: SurveyFieldOption[];
  [key: string]: unknown;
};

export type Survey = {
  id: string;
  organization_id?: string;
  name: string;
  code: string;
  description?: string | null;
  category?: string | null;
  status: string;
  current_version: number;
  updated_at?: string;
};

export type SurveyVersion = {
  id: string;
  survey_id: string;
  version: number;
  title: string;
  schema: { fields?: SurveyField[]; pages?: unknown[]; [key: string]: unknown };
  published_at?: string | null;
  created_at?: string;
};

export type SurveyDetail = {
  survey: Survey;
  version: SurveyVersion;
};

export type SurveySubmission = {
  id: string;
  survey_id: string;
  survey_version_id: string;
  version: number;
  status: string;
  answers: Record<string, unknown>;
  respondent_name?: string | null;
  beneficiary_id?: string | null;
  client_mutation_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type Task = {
  id: string;
  organization_id?: string;
  project_id?: string;
  activity_id?: string | null;
  title: string;
  description?: string | null;
  status: string;
  priority?: string | null;
  assignee_id?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  updated_at?: string;
};

export type Notification = {
  id: string;
  organization_id?: string;
  user_id?: string;
  event_type?: string;
  title: string;
  body?: string | null;
  link?: string | null;
  severity?: string | null;
  status?: string | null;
  read_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type Device = {
  id: string;
  organization_id: string;
  user_id: string;
  device_key: string;
  name: string;
  platform: string;
  app_version?: string | null;
  status: string;
  last_seen_at?: string | null;
  last_sync_at?: string | null;
  storage_bytes?: number;
  pending_uploads?: number;
};

export type SyncMutationItem = {
  client_mutation_id: string;
  entity_type: string;
  op: string;
  local_id?: string;
  payload: Record<string, unknown>;
  created_at?: string;
};

export type SyncRunResponse = {
  session_id: string;
  status: string;
  push: {
    applied?: number;
    failed?: number;
    results: Array<{
      client_mutation_id: string;
      status: string;
      server_id?: string;
      error?: string;
      local_id?: string;
      entity_type?: string;
      record?: Record<string, unknown>;
    }>;
  };
  pull: Record<string, unknown> & { sync_token?: string };
  sync_token?: string;
};

type Paginated<T> = { items: T[]; meta: { total: number; page: number; page_size: number } };

type ApiErrorBody = {
  message?: string;
  code?: string;
  details?: unknown;
  detail?: string | { message?: string } | Array<{ msg?: string }>;
};

function humanApiError(body: ApiErrorBody, status: number): string {
  if (typeof body.message === "string" && body.message.trim()) {
    return body.message.trim();
  }
  if (typeof body.detail === "string" && body.detail.trim()) {
    return body.detail.trim();
  }
  if (body.detail && typeof body.detail === "object" && !Array.isArray(body.detail)) {
    const nested = body.detail.message;
    if (typeof nested === "string" && nested.trim()) return nested.trim();
  }
  if (Array.isArray(body.detail) && body.detail.length > 0) {
    const first = body.detail[0]?.msg;
    if (typeof first === "string" && first.trim()) return first.trim();
  }
  if (status === 401) return "Invalid email or password";
  if (status === 403) return "You do not have permission to do that";
  if (status === 404) return "Not found";
  if (status === 429) return "Too many requests. Please try again later.";
  if (status >= 500) return "Something went wrong. Please try again.";
  return "Request failed. Please try again.";
}

class FieldApi {
  accessToken: string | null = null;
  refreshToken: string | null = null;
  organizationId: string | null = null;

  setSession(tokens: {
    access_token: string;
    refresh_token: string;
    organization_id?: string | null;
  }) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    this.organizationId = tokens.organization_id ?? this.organizationId;
  }

  clearSession() {
    this.accessToken = null;
    this.refreshToken = null;
    this.organizationId = null;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true,
  ): Promise<T> {
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);

    const res = await fetch(`${API_V1}${path}`, { ...options, headers }).catch(() => {
      throw new Error("Unable to reach the server. Check your connection and try again.");
    });

    if (res.status === 401 && retry && this.refreshToken) {
      const ok = await this.refresh();
      if (ok) return this.request<T>(path, options, false);
      this.clearSession();
    }

    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as ApiErrorBody;
      throw new Error(humanApiError(body, res.status));
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  }

  async refresh(): Promise<boolean> {
    if (!this.refreshToken) return false;
    try {
      const res = await fetch(`${API_V1}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (!res.ok) return false;
      const data = (await res.json()) as Tokens;
      if (!data.access_token || !data.refresh_token) return false;
      const orgId =
        data.user?.primary_organization_id ?? this.organizationId;
      this.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        organization_id: orgId,
      });
      await SecureStore.setItemAsync(ACCESS_KEY, data.access_token);
      await SecureStore.setItemAsync(REFRESH_KEY, data.refresh_token);
      if (orgId) await SecureStore.setItemAsync(ORG_KEY, orgId);
      return true;
    } catch {
      return false;
    }
  }

  login(email: string, password: string) {
    return this.request<Tokens>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
      false,
    );
  }

  listBeneficiaries(params: { page?: number; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Beneficiary>>(`/beneficiaries?${q}`);
  }

  createBeneficiary(body: Record<string, unknown>) {
    return this.request<Beneficiary>("/beneficiaries", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateBeneficiary(id: string, body: Record<string, unknown>) {
    return this.request<Beneficiary>(`/beneficiaries/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listCommunities(params: { page?: number; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Community>>(`/communities?${q}`);
  }

  createCommunity(body: Record<string, unknown>) {
    return this.request<Community>("/communities", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listHouseholds(params: { page?: number; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Household>>(`/households?${q}`);
  }

  createHousehold(body: Record<string, unknown>) {
    return this.request<Household>("/households", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listSurveys(params: { status?: string; page?: number; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.status) q.set("status", params.status);
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Survey>>(`/surveys?${q}`);
  }

  getSurvey(id: string) {
    return this.request<SurveyDetail>(`/surveys/${id}`);
  }

  submitSurveyResponse(id: string, body: Record<string, unknown>) {
    return this.request<SurveySubmission>(`/surveys/${id}/responses`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listSurveyResponses(
    params: { survey_id?: string; page?: number; updated_after?: string } = {},
  ) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.survey_id) q.set("survey_id", params.survey_id);
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<SurveySubmission>>(`/survey-responses?${q}`);
  }

  registerDevice(body: {
    device_key: string;
    name: string;
    platform: string;
    app_version?: string;
    push_token?: string;
    storage_bytes?: number;
    pending_uploads?: number;
    metadata?: Record<string, unknown>;
  }) {
    return this.request<Device>("/devices/register", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  heartbeat(
    deviceId: string,
    body: {
      app_version?: string;
      storage_bytes?: number;
      pending_uploads?: number;
      metadata?: Record<string, unknown>;
    } = {},
  ) {
    return this.request<Device>(`/devices/${deviceId}/heartbeat`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  syncRun(body: {
    device_id: string;
    client_version?: string;
    push?: {
      device_id?: string;
      mutations: SyncMutationItem[];
    };
    pull?: {
      since?: string;
      entities?: string[];
      page_size?: number;
    };
  }) {
    return this.request<SyncRunResponse>("/sync/run", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTasks(params: { page?: number; status?: string; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.status) q.set("status", params.status);
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Task>>(`/tasks?${q}`);
  }

  listNotifications(params: { page?: number; unread_only?: boolean; updated_after?: string } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", "100");
    if (params.unread_only) q.set("unread_only", "true");
    if (params.updated_after) q.set("updated_after", params.updated_after);
    return this.request<Paginated<Notification>>(`/notifications?${q}`);
  }
}

export const api = new FieldApi();
