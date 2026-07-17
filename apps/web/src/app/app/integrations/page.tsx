"use client";

import { FeatureGate } from "@/components/feature-gate";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Copy,
  Download,
  HeartPulse,
  KeyRound,
  Plug,
  RefreshCw,
  Webhook,
} from "lucide-react";
import {
  api,
  type ConnectorDefinition,
  type FieldMappingPreview,
  type IntegrationConnection,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const HUB_TABS = [
  { id: "gallery", label: "Gallery" },
  { id: "connections", label: "Connections" },
  { id: "api-keys", label: "API Keys" },
  { id: "webhooks", label: "Webhooks" },
  { id: "monitoring", label: "Monitoring" },
  { id: "mappings", label: "Mappings" },
];

const CATEGORY_LABELS: Record<string, string> = {
  productivity: "Productivity",
  data_collection: "Data collection",
  messaging: "Messaging",
  analytics: "Analytics",
  finance: "Finance",
  crm: "CRM",
  development: "Development",
  storage: "Storage",
};

function categoryLabel(code: string) {
  return CATEGORY_LABELS[code] ?? code.replaceAll("_", " ");
}

function KpiTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-stone-100 bg-stone-50/60 px-3 py-3 dark:border-stone-800 dark:bg-stone-900/40">
      <p className="text-[11px] font-medium uppercase tracking-wider text-stone-400">
        {label}
      </p>
      <p className="mt-1 font-display text-2xl font-semibold tabular-nums tracking-tight">
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-xs text-stone-500">{hint}</p> : null}
    </div>
  );
}

function GalleryTab({ onEnabled }: { onEnabled: () => void }) {
  const [category, setCategory] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [enabling, setEnabling] = useState<string | null>(null);
  const [endpointByCode, setEndpointByCode] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: () => api.listConnectors({ include_future: true }),
  });

  const categories = useMemo(() => {
    const set = new Set((connectors.data?.items ?? []).map((c) => c.category));
    return Array.from(set).sort();
  }, [connectors.data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (connectors.data?.items ?? []).filter((c) => {
      if (category !== "all" && c.category !== category) return false;
      if (!q) return true;
      return (
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q) ||
        (c.description ?? "").toLowerCase().includes(q)
      );
    });
  }, [connectors.data, category, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, ConnectorDefinition[]>();
    for (const c of filtered) {
      const list = map.get(c.category) ?? [];
      list.push(c);
      map.set(c.category, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  const enable = useMutation({
    mutationFn: (connector: ConnectorDefinition) =>
      api.enableConnector({
        connector_code: connector.code,
        name: connector.name,
        endpoint_url: endpointByCode[connector.code] || undefined,
        events: ["report.published", "prediction.opened", "webhook.received"],
      }),
    onSuccess: async () => {
      setError(null);
      setEnabling(null);
      onEnabled();
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <Label htmlFor="connector-search">Search connectors</Label>
          <Input
            id="connector-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Kobo, Slack, Power BI…"
          />
        </div>
        <div>
          <Label htmlFor="connector-category">Category</Label>
          <select
            id="connector-category"
            className="mt-1 w-full min-w-[160px] rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {categoryLabel(c)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {connectors.isLoading && (
        <p className="text-sm text-stone-400">Loading connector catalog…</p>
      )}

      {!connectors.isLoading && grouped.length === 0 && (
        <EmptyState
          title="No connectors match"
          description="Try another category or clear the search."
        />
      )}

      {grouped.map(([cat, items]) => (
        <div key={cat} className="space-y-3">
          <h2 className="font-display text-lg font-semibold tracking-tight text-stone-800 dark:text-stone-100">
            {categoryLabel(cat)}
          </h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((connector) => {
              const isFuture = connector.status === "future_ready";
              const needsEndpoint =
                connector.auth_type === "webhook" ||
                connector.code.includes("webhook") ||
                connector.code === "slack";
              return (
                <Card key={connector.code} className="flex flex-col">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <CardTitle className="text-base">{connector.name}</CardTitle>
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge status={connector.auth_type} />
                      {isFuture && <StatusBadge status="future" />}
                    </div>
                  </div>
                  <CardDescription className="mt-2 line-clamp-3">
                    {connector.description ?? "Connector for ImpactFlow."}
                  </CardDescription>
                  <p className="mt-3 text-xs text-stone-400">
                    {connector.code}
                    {connector.version ? ` · v${connector.version}` : ""}
                    {connector.sync_modes?.length
                      ? ` · ${connector.sync_modes.join("/")}`
                      : ""}
                  </p>
                  {needsEndpoint && enabling === connector.code && (
                    <div className="mt-3">
                      <Label htmlFor={`ep-${connector.code}`}>Endpoint URL</Label>
                      <Input
                        id={`ep-${connector.code}`}
                        value={endpointByCode[connector.code] ?? ""}
                        onChange={(e) =>
                          setEndpointByCode((prev) => ({
                            ...prev,
                            [connector.code]: e.target.value,
                          }))
                        }
                        placeholder="https://hooks.example.com/…"
                      />
                    </div>
                  )}
                  <div className="mt-auto flex flex-wrap gap-2 pt-4">
                    {enabling === connector.code ? (
                      <>
                        <Button
                          size="sm"
                          disabled={enable.isPending || isFuture}
                          onClick={() => enable.mutate(connector)}
                        >
                          {enable.isPending ? "Enabling…" : "Confirm enable"}
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setEnabling(null)}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        disabled={isFuture}
                        onClick={() => setEnabling(connector.code)}
                      >
                        {isFuture ? "Coming soon" : "Enable"}
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConnectionsTab() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [healthMsg, setHealthMsg] = useState<Record<string, string>>({});
  const [exportJson, setExportJson] = useState<string | null>(null);

  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.listIntegrations(),
  });

  const invalidate = async () => {
    await qc.invalidateQueries({ queryKey: ["integrations"] });
    await qc.invalidateQueries({ queryKey: ["integration-monitoring"] });
    await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const test = useMutation({
    mutationFn: (id: string) => api.testIntegration(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const health = useMutation({
    mutationFn: (id: string) => api.integrationHealth(id),
    onSuccess: (result, id) => {
      setHealthMsg((prev) => ({
        ...prev,
        [id]: result.healthy
          ? result.message || "Healthy"
          : result.message || "Unhealthy",
      }));
      void invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const sync = useMutation({
    mutationFn: (id: string) =>
      api.syncIntegration(id, { mode: "incremental", direction: "pull" }),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const clone = useMutation({
    mutationFn: (id: string) => api.cloneIntegration(id),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  const exportMut = useMutation({
    mutationFn: (id: string) => api.exportIntegration(id),
    onSuccess: (data) => {
      setExportJson(JSON.stringify(data, null, 2));
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const oauth = useMutation({
    mutationFn: (item: IntegrationConnection) =>
      api.startIntegrationOAuth(item.id, {
        redirect_uri: `${window.location.origin}/app/integrations`,
        connector_code: item.provider,
      }),
    onSuccess: (data) => {
      if (data.authorize_url) window.open(data.authorize_url, "_blank");
    },
    onError: (err: Error) => setError(err.message),
  });

  const items = integrations.data?.items ?? [];

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {exportJson && (
        <Card className="border-teal-200 bg-teal-50/80 dark:border-teal-900 dark:bg-teal-950/30">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle>Exported settings</CardTitle>
              <CardDescription>Secrets are redacted. Copy or download as needed.</CardDescription>
            </div>
            <Button variant="secondary" size="sm" onClick={() => setExportJson(null)}>
              Dismiss
            </Button>
          </div>
          <pre className="mt-3 max-h-64 overflow-auto rounded-xl bg-white p-3 text-xs dark:bg-stone-950">
            {exportJson}
          </pre>
        </Card>
      )}

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Active connections</CardTitle>
            <CardDescription>
              Health checks, sync, clone, and export for enabled connectors.
            </CardDescription>
          </div>
          <Link
            href="/app/developer"
            className="text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
          >
            Developer portal →
          </Link>
        </div>

        <div className="mt-4 space-y-3">
          {integrations.isLoading && (
            <p className="text-sm text-stone-400">Loading connections…</p>
          )}
          {!integrations.isLoading && items.length === 0 && (
            <EmptyState
              title="No connections yet"
              description="Enable a connector from the Gallery tab to get started."
            />
          )}
          {items.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-stone-200 px-4 py-3 dark:border-stone-800"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{item.name}</div>
                  <div className="mt-0.5 text-xs text-stone-400">
                    {item.provider} · {item.direction}
                    {item.endpoint_url ? ` · ${item.endpoint_url}` : ""}
                    {item.last_sync_at
                      ? ` · synced ${new Date(item.last_sync_at).toLocaleString()}`
                      : ""}
                  </div>
                  {healthMsg[item.id] && (
                    <p
                      className={cn(
                        "mt-1 text-xs",
                        healthMsg[item.id].toLowerCase().includes("missing") ||
                          healthMsg[item.id].toLowerCase().includes("unhealthy")
                          ? "text-amber-600"
                          : "text-teal-700 dark:text-teal-300",
                      )}
                    >
                      {healthMsg[item.id]}
                    </p>
                  )}
                  {item.last_error && (
                    <p className="mt-1 text-xs text-rose-600">{item.last_error}</p>
                  )}
                </div>
                <StatusBadge status={item.status} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => health.mutate(item.id)}
                  disabled={health.isPending}
                >
                  <HeartPulse className="h-3.5 w-3.5" />
                  Health
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => sync.mutate(item.id)}
                  disabled={sync.isPending}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Sync
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => test.mutate(item.id)}
                  disabled={test.isPending}
                >
                  Test
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => clone.mutate(item.id)}
                  disabled={clone.isPending}
                >
                  <Copy className="h-3.5 w-3.5" />
                  Clone
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => exportMut.mutate(item.id)}
                  disabled={exportMut.isPending}
                >
                  <Download className="h-3.5 w-3.5" />
                  Export
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => oauth.mutate(item)}
                  disabled={oauth.isPending}
                >
                  OAuth
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ApiKeysTab() {
  const qc = useQueryClient();
  const [keyName, setKeyName] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const keys = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.listApiKeys(),
  });

  const createKey = useMutation({
    mutationFn: () => api.createApiKey({ name: keyName, scopes: ["read", "write"] }),
    onSuccess: async (row) => {
      setKeyName("");
      setCreatedSecret(row.secret);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      await qc.invalidateQueries({ queryKey: ["integration-monitoring"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.revokeApiKey(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      await qc.invalidateQueries({ queryKey: ["integration-monitoring"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const rotate = useMutation({
    mutationFn: (id: string) => api.rotateApiKey(id),
    onSuccess: async (row) => {
      setCreatedSecret(row.secret);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {createdSecret && (
        <Card className="border-teal-200 bg-teal-50 dark:border-teal-900 dark:bg-teal-950/30">
          <CardTitle>Copy your API key now</CardTitle>
          <CardDescription>
            This secret is shown once. Store it securely — it cannot be retrieved later.
          </CardDescription>
          <code className="mt-3 block break-all rounded-xl bg-white px-3 py-2 text-sm dark:bg-stone-950">
            {createdSecret}
          </code>
          <Button
            className="mt-3"
            variant="secondary"
            size="sm"
            onClick={() => void navigator.clipboard.writeText(createdSecret)}
          >
            <Copy className="h-3.5 w-3.5" />
            Copy
          </Button>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Create API key</CardTitle>
          <CardDescription>
            Use with <code className="text-xs">X-Api-Key</code> or Bearer{" "}
            <code className="text-xs">if_…</code>.
          </CardDescription>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createKey.mutate();
            }}
          >
            <div>
              <Label htmlFor="keyName">Key name</Label>
              <Input
                id="keyName"
                required
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="Reporting ETL"
              />
            </div>
            <Button type="submit" disabled={createKey.isPending}>
              {createKey.isPending ? "Creating…" : "Generate key"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Issued keys</CardTitle>
          <div className="mt-4 space-y-2">
            {keys.data?.items.map((key) => (
              <div
                key={key.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
              >
                <div>
                  <div className="font-medium">{key.name}</div>
                  <div className="font-mono text-xs text-stone-400">
                    {key.key_prefix}… · {(key.scopes ?? []).join(", ") || "read"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={key.status} />
                  {key.status === "active" && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => rotate.mutate(key.id)}
                        disabled={rotate.isPending}
                      >
                        Rotate
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => revoke.mutate(key.id)}
                        disabled={revoke.isPending}
                      >
                        Revoke
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
            {(keys.data?.items.length ?? 0) === 0 && (
              <p className="text-sm text-stone-400">No API keys yet.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function WebhooksTab() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [redriveMsg, setRedriveMsg] = useState<string | null>(null);

  const deliveries = useQuery({
    queryKey: ["webhook-deliveries", statusFilter],
    queryFn: () =>
      api.listWebhookDeliveries({
        status: statusFilter || undefined,
      }),
  });

  const redrive = useMutation({
    mutationFn: () => api.redriveDeadWebhooks(25),
    onSuccess: async (result) => {
      setRedriveMsg(`Requeued ${result.redriven} dead-letter delivery(ies).`);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["webhook-deliveries"] });
      await qc.invalidateQueries({ queryKey: ["integration-monitoring"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const items = deliveries.data?.items ?? [];

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {redriveMsg && <p className="text-sm text-teal-700 dark:text-teal-300">{redriveMsg}</p>}

      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <CardTitle>Webhook deliveries</CardTitle>
            <CardDescription>
              Outbound delivery log with retries and dead-letter queue.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <Label htmlFor="wh-status">Status</Label>
              <select
                id="wh-status"
                className="mt-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="delivered">Delivered</option>
                <option value="failed">Failed</option>
                <option value="dead">Dead</option>
              </select>
            </div>
            <Button
              variant="secondary"
              onClick={() => redrive.mutate()}
              disabled={redrive.isPending}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {redrive.isPending ? "Redriving…" : "Redrive dead"}
            </Button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {deliveries.isLoading && (
            <p className="text-sm text-stone-400">Loading deliveries…</p>
          )}
          {!deliveries.isLoading && items.length === 0 && (
            <EmptyState
              title="No webhook deliveries"
              description="Outbound webhook events will appear here once integrations fire."
            />
          )}
          {items.map((row) => (
            <div
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
            >
              <div>
                <div className="font-medium">{row.event_type}</div>
                <div className="text-xs text-stone-400">
                  attempt {row.attempt_count}/{row.max_attempts}
                  {row.endpoint_url ? ` · ${row.endpoint_url}` : ""}
                  {row.response_status != null ? ` · HTTP ${row.response_status}` : ""}
                  {" · "}
                  {new Date(row.created_at).toLocaleString()}
                </div>
                {row.last_error && (
                  <p className="mt-1 text-xs text-rose-600">{row.last_error}</p>
                )}
              </div>
              <StatusBadge status={row.status} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function MonitoringTab() {
  const monitoring = useQuery({
    queryKey: ["integration-monitoring"],
    queryFn: () => api.integrationMonitoring(),
    refetchInterval: 60_000,
  });

  const syncJobs = useQuery({
    queryKey: ["sync-jobs"],
    queryFn: () => api.listSyncJobs({ page_size: 20 }),
  });

  const m = monitoring.data;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Connected systems"
          value={m ? String(m.connected_systems) : "…"}
        />
        <KpiTile
          label="Healthy"
          value={m ? String(m.healthy_connectors) : "…"}
          hint={m ? `${m.errored_connectors} errored` : undefined}
        />
        <KpiTile
          label="Webhook success"
          value={m ? `${m.success_rate}%` : "…"}
          hint={
            m
              ? `${m.webhook_delivered} delivered · ${m.webhook_dead} dead · ${m.webhook_pending} pending`
              : undefined
          }
        />
        <KpiTile
          label="Sync jobs"
          value={m ? String(m.sync_completed) : "…"}
          hint={m ? `${m.sync_failed} failed · ${m.api_keys_active} API keys` : undefined}
        />
      </div>

      <Card>
        <CardTitle>Recent sync jobs</CardTitle>
        <CardDescription>Last connector sync runs for this organization.</CardDescription>
        <div className="mt-4 space-y-2">
          {syncJobs.isLoading && (
            <p className="text-sm text-stone-400">Loading sync jobs…</p>
          )}
          {!syncJobs.isLoading && (syncJobs.data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No sync jobs yet.</p>
          )}
          {syncJobs.data?.items.map((job) => (
            <div
              key={job.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
            >
              <div>
                <div className="font-medium">
                  {job.connector_code} · {job.mode}/{job.direction}
                </div>
                <div className="text-xs text-stone-400">
                  {job.records_processed} processed
                  {job.records_failed ? ` · ${job.records_failed} failed` : ""}
                  {job.created_at
                    ? ` · ${new Date(job.created_at).toLocaleString()}`
                    : ""}
                </div>
                {job.error_message && (
                  <p className="mt-1 text-xs text-rose-600">{job.error_message}</p>
                )}
              </div>
              <StatusBadge status={job.status} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function MappingsTab() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [entityType, setEntityType] = useState("beneficiary");
  const [connectorCode, setConnectorCode] = useState("kobo");
  const [sourceField, setSourceField] = useState("first");
  const [targetField, setTargetField] = useState("first_name");
  const [sampleJson, setSampleJson] = useState('{"first":"Amina","last":"Okello"}');
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [preview, setPreview] = useState<FieldMappingPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mappings = useQuery({
    queryKey: ["field-mappings"],
    queryFn: () => api.listFieldMappings(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createFieldMapping({
        name,
        entity_type: entityType,
        connector_code: connectorCode || undefined,
        mappings: [
          { source: sourceField, target: targetField },
          ...(sourceField === "first" && targetField === "first_name"
            ? [{ source: "last", target: "last_name" }]
            : []),
        ],
        defaults: entityType === "beneficiary" ? { consent_data_use: true } : undefined,
        validation_rules: [{ field: targetField, required: true }],
      }),
    onSuccess: async (row) => {
      setName("");
      setPreviewId(row.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["field-mappings"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const runPreview = useMutation({
    mutationFn: async () => {
      if (!previewId) throw new Error("Select or create a mapping profile first");
      let sample: Record<string, unknown>;
      try {
        sample = JSON.parse(sampleJson) as Record<string, unknown>;
      } catch {
        throw new Error("Sample must be valid JSON");
      }
      return api.previewFieldMapping(previewId, sample);
    },
    onSuccess: (result) => {
      setPreview(result);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Create mapping profile</CardTitle>
          <CardDescription>
            Map external fields into ImpactFlow entities for connector sync.
          </CardDescription>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <div>
              <Label htmlFor="map-name">Name</Label>
              <Input
                id="map-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Kobo Beneficiary Map"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="map-entity">Entity type</Label>
                <select
                  id="map-entity"
                  className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                >
                  <option value="beneficiary">Beneficiary</option>
                  <option value="household">Household</option>
                  <option value="community">Community</option>
                  <option value="survey_response">Survey response</option>
                  <option value="indicator_result">Indicator result</option>
                </select>
              </div>
              <div>
                <Label htmlFor="map-connector">Connector code</Label>
                <Input
                  id="map-connector"
                  value={connectorCode}
                  onChange={(e) => setConnectorCode(e.target.value)}
                  placeholder="kobo"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="map-source">Source field</Label>
                <Input
                  id="map-source"
                  value={sourceField}
                  onChange={(e) => setSourceField(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="map-target">Target field</Label>
                <Input
                  id="map-target"
                  value={targetField}
                  onChange={(e) => setTargetField(e.target.value)}
                />
              </div>
            </div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create profile"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Preview mapping</CardTitle>
          <CardDescription>Apply a profile to a sample external payload.</CardDescription>
          <div className="mt-4 space-y-3">
            <div>
              <Label htmlFor="map-profile">Profile</Label>
              <select
                id="map-profile"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={previewId ?? ""}
                onChange={(e) => {
                  setPreviewId(e.target.value || null);
                  setPreview(null);
                }}
              >
                <option value="">Select profile…</option>
                {mappings.data?.items.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="map-sample">Sample JSON</Label>
              <textarea
                id="map-sample"
                className="mt-1 min-h-[100px] w-full rounded-xl border border-stone-200 bg-white px-3 py-2 font-mono text-xs dark:border-stone-800 dark:bg-stone-950"
                value={sampleJson}
                onChange={(e) => setSampleJson(e.target.value)}
              />
            </div>
            <Button
              onClick={() => runPreview.mutate()}
              disabled={runPreview.isPending || !previewId}
            >
              {runPreview.isPending ? "Previewing…" : "Run preview"}
            </Button>
            {preview && (
              <div className="rounded-xl border border-stone-200 bg-stone-50/80 p-3 dark:border-stone-800 dark:bg-stone-900/40">
                <div className="flex items-center gap-2">
                  <StatusBadge status={preview.valid ? "valid" : "invalid"} />
                  {!preview.valid && preview.errors.length > 0 && (
                    <span className="text-xs text-rose-600">
                      {preview.errors.join("; ")}
                    </span>
                  )}
                </div>
                <pre className="mt-2 overflow-auto text-xs">
                  {JSON.stringify(preview.mapped, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>Saved profiles</CardTitle>
        <div className="mt-4 space-y-2">
          {(mappings.data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No mapping profiles yet.</p>
          )}
          {mappings.data?.items.map((m) => (
            <div
              key={m.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
            >
              <div>
                <div className="font-medium">{m.name}</div>
                <div className="text-xs text-stone-400">
                  {m.code} · {m.entity_type}
                  {m.connector_code ? ` · ${m.connector_code}` : ""} ·{" "}
                  {(m.mappings ?? []).length} rules
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={m.status} />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setPreviewId(m.id);
                    setPreview(null);
                  }}
                >
                  Preview
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <FeatureGate feature="integrations" fallbackTitle="Integrations require Professional+">
      <IntegrationsInner />
    </FeatureGate>
  );
}

function IntegrationsInner() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("gallery");

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Integrations Hub
          </h1>
          <p className="mt-2 max-w-2xl text-stone-500">
            Browse connectors, manage connections, API keys, webhooks, field mappings, and
            health — wired to ImpactFlow API 0.18.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/app/developer">
            <Button variant="secondary" size="sm">
              <KeyRound className="h-3.5 w-3.5" />
              Developer portal
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-stone-500">
        <span className="inline-flex items-center gap-1 rounded-lg bg-white/70 px-2 py-1 dark:bg-stone-900/50">
          <Plug className="h-3 w-3 text-teal-700" /> Gallery
        </span>
        <span className="inline-flex items-center gap-1 rounded-lg bg-white/70 px-2 py-1 dark:bg-stone-900/50">
          <Activity className="h-3 w-3 text-teal-700" /> Monitoring
        </span>
        <span className="inline-flex items-center gap-1 rounded-lg bg-white/70 px-2 py-1 dark:bg-stone-900/50">
          <Webhook className="h-3 w-3 text-teal-700" /> Webhooks
        </span>
      </div>

      <Tabs items={HUB_TABS} active={tab} onChange={setTab} />

      {tab === "gallery" && (
        <GalleryTab
          onEnabled={() => {
            void qc.invalidateQueries({ queryKey: ["integrations"] });
            void qc.invalidateQueries({ queryKey: ["integration-monitoring"] });
            void qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
            setTab("connections");
          }}
        />
      )}
      {tab === "connections" && <ConnectionsTab />}
      {tab === "api-keys" && <ApiKeysTab />}
      {tab === "webhooks" && <WebhooksTab />}
      {tab === "monitoring" && <MonitoringTab />}
      {tab === "mappings" && <MappingsTab />}
    </div>
  );
}
