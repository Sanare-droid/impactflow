/**
 * Field app API client — mirrors web auth session patterns.
 * Set EXPO_PUBLIC_API_URL to your machine LAN IP for device testing.
 */
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
  code: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  status: string;
};

type Paginated<T> = { items: T[]; meta: { total: number } };

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

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);

    const res = await fetch(`${API_V1}${path}`, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || body.detail || `Request failed (${res.status})`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  }

  login(email: string, password: string) {
    return this.request<Tokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  listBeneficiaries() {
    return this.request<Paginated<Beneficiary>>("/beneficiaries?page_size=50");
  }

  createBeneficiary(body: Record<string, unknown>) {
    return this.request<Beneficiary>("/beneficiaries", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }
}

export const api = new FieldApi();
