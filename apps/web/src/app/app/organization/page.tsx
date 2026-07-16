"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function OrganizationAdminPage() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [hostname, setHostname] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [financialYear, setFinancialYear] = useState("January");
  const [retentionDays, setRetentionDays] = useState("365");
  const [issuer, setIssuer] = useState("");
  const [clientId, setClientId] = useState("");

  const org = useQuery({ queryKey: ["organization"], queryFn: () => api.currentOrganization() });
  const domains = useQuery({ queryKey: ["domains"], queryFn: () => api.listDomains() });
  const backups = useQuery({ queryKey: ["backups"], queryFn: () => api.listBackups() });
  const locales = useQuery({ queryKey: ["locales"], queryFn: () => api.listLocales() });
  const features = useQuery({ queryKey: ["features"], queryFn: () => api.getFeatures() });

  useEffect(() => {
    const s = org.data?.settings ?? {};
    if (typeof s.currency === "string") setCurrency(s.currency);
    if (typeof s.financial_year_start === "string") setFinancialYear(s.financial_year_start);
    if (typeof s.data_retention_days === "number") setRetentionDays(String(s.data_retention_days));
  }, [org.data]);

  const saveSettings = useMutation({
    mutationFn: () =>
      api.patchAdminSettings({
        currency,
        financial_year_start: financialYear,
        data_retention_days: Number(retentionDays) || 365,
        security: {
          session_timeout_minutes: 480,
          password_min_length: 12,
          mfa_recommended: true,
        },
      }),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["organization"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const addDomain = useMutation({
    mutationFn: () => api.createDomain({ hostname, is_primary: true }),
    onSuccess: async () => {
      setHostname("");
      await qc.invalidateQueries({ queryKey: ["domains"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const verify = useMutation({
    mutationFn: (id: string) => api.verifyDomain(id),
    onSuccess: async () => qc.invalidateQueries({ queryKey: ["domains"] }),
    onError: (err: Error) => setError(err.message),
  });

  const backup = useMutation({
    mutationFn: () => api.createBackup({ label: `Manual ${new Date().toISOString().slice(0, 10)}` }),
    onSuccess: async () => qc.invalidateQueries({ queryKey: ["backups"] }),
    onError: (err: Error) => setError(err.message),
  });

  const sso = useMutation({
    mutationFn: () =>
      api.upsertSso({
        provider: "oidc",
        config: { issuer, client_id: clientId },
        allowed_domains: [],
      }),
    onError: (err: Error) => setError(err.message),
  });

  async function onSettings(e: FormEvent) {
    e.preventDefault();
    await saveSettings.mutateAsync();
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Organization administration
        </h1>
        <p className="mt-2 text-stone-500">
          Tenant settings, domains, security, localization, and backups — one console.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="text-teal-800 underline-offset-2 hover:underline dark:text-teal-300" href="/app/billing">
          Billing
        </Link>
        <Link className="text-teal-800 underline-offset-2 hover:underline dark:text-teal-300" href="/app/branding">
          White label
        </Link>
        <Link className="text-teal-800 underline-offset-2 hover:underline dark:text-teal-300" href="/app/onboarding">
          Onboarding
        </Link>
        <Link className="text-teal-800 underline-offset-2 hover:underline dark:text-teal-300" href="/app/customer-success">
          Customer success
        </Link>
      </div>

      <Card>
        <CardTitle>{org.data?.name ?? "Organization"}</CardTitle>
        <CardDescription>
          {org.data?.slug} · {org.data?.timezone} · {org.data?.locale}
        </CardDescription>
        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase text-stone-500">Country</dt>
            <dd className="font-medium">{org.data?.country_code ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-stone-500">Type</dt>
            <dd className="font-medium">{org.data?.organization_type}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-stone-500">Verified</dt>
            <dd className="font-medium">{org.data?.is_verified ? "Yes" : "No"}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <CardTitle>Regional & retention</CardTitle>
        <form className="mt-4 grid gap-4 sm:grid-cols-3" onSubmit={onSettings}>
          <div>
            <Label htmlFor="currency">Currency</Label>
            <Input id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="fy">Financial year start</Label>
            <Input
              id="fy"
              value={financialYear}
              onChange={(e) => setFinancialYear(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="retention">Data retention (days)</Label>
            <Input
              id="retention"
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={saveSettings.isPending}>
            Save policies
          </Button>
        </form>
      </Card>

      <Card>
        <CardTitle>Custom domains</CardTitle>
        <CardDescription>DNS verification + SSL readiness for white-label portals.</CardDescription>
        <form
          className="mt-4 flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addDomain.mutate();
          }}
        >
          <Input
            placeholder="portal.organization.org"
            value={hostname}
            onChange={(e) => setHostname(e.target.value)}
            className="max-w-md"
          />
          <Button type="submit" disabled={!hostname || addDomain.isPending}>
            Add domain
          </Button>
        </form>
        <div className="mt-4 space-y-3">
          {(domains.data?.items ?? []).map((d) => (
            <div
              key={d.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 px-4 py-3 dark:border-stone-800"
            >
              <div>
                <div className="font-medium">{d.hostname}</div>
                <div className="text-xs text-stone-500">
                  TXT verify · SSL {d.ssl_status}
                  {d.is_primary ? " · primary" : ""}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={d.status} />
                {d.status !== "active" && (
                  <Button variant="secondary" onClick={() => verify.mutate(d.id)}>
                    Verify
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardTitle>SSO foundation</CardTitle>
        <CardDescription>OIDC / SAML / Azure AD / Google Workspace ready — secrets encrypted.</CardDescription>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="issuer">Issuer URL</Label>
            <Input id="issuer" value={issuer} onChange={(e) => setIssuer(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="client">Client ID</Label>
            <Input id="client" value={clientId} onChange={(e) => setClientId(e.target.value)} />
          </div>
        </div>
        <Button
          className="mt-3"
          variant="secondary"
          disabled={!issuer || !clientId || sso.isPending}
          onClick={() => sso.mutate()}
        >
          Save OIDC draft
        </Button>
      </Card>

      <Card>
        <CardTitle>Language packs</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {(locales.data?.items ?? []).map((l) => (
            <span
              key={l.locale}
              className="rounded-lg bg-stone-100 px-2.5 py-1 text-xs dark:bg-stone-900"
            >
              {l.native_name} ({l.locale}) · {l.direction}
            </span>
          ))}
        </div>
      </Card>

      <Card>
        <CardTitle>Feature access</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(features.data?.features ?? {})
            .filter(([, on]) => on)
            .map(([code]) => (
              <span
                key={code}
                className="rounded-lg bg-teal-100 px-2.5 py-1 text-xs text-teal-900 dark:bg-teal-900/40 dark:text-teal-100"
              >
                {code}
              </span>
            ))}
        </div>
      </Card>

      <Card>
        <CardTitle>Backups & export</CardTitle>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button onClick={() => backup.mutate()} disabled={backup.isPending}>
            Create restore point
          </Button>
          <Button
            variant="secondary"
            onClick={async () => {
              const data = await api.exportTenantData();
              const blob = new Blob([JSON.stringify(data, null, 2)], {
                type: "application/json",
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "impactflow-export.json";
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            Export all data
          </Button>
        </div>
        <ul className="mt-4 space-y-2 text-sm">
          {(backups.data?.items ?? []).map((b) => (
            <li key={b.id} className="flex justify-between gap-3 rounded-xl bg-stone-50 px-3 py-2 dark:bg-stone-900">
              <span>{b.label}</span>
              <span className="text-stone-500">{b.status} · {b.size_bytes} B</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
