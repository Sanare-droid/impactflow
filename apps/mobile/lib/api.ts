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

type Paginated<T> = { items: T[]; meta: { total: number; page: number; page_size: number } };

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

    const res = await fetch(`${API_V1}${path}`, { ...options, headers });

    if (res.status === 401 && retry && this.refreshToken) {
      const ok = await this.refresh();
      if (ok) return this.request<T>(path, options, false);
      this.clearSession();
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const message =
        body.message ||
        (typeof body.detail === "string" ? body.detail : null) ||
        `Request failed (${res.status})`;
      throw new Error(message);
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
    return this.request<Tokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
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
}

export const api = new FieldApi();
