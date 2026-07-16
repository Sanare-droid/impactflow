"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function IntegrationsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("webhook");
  const [endpoint, setEndpoint] = useState("");
  const [secret, setSecret] = useState("");
  const [keyName, setKeyName] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.listIntegrations(),
  });
  const keys = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.listApiKeys(),
  });

  const createIntegration = useMutation({
    mutationFn: () =>
      api.createIntegration({
        name,
        provider,
        endpoint_url: endpoint || undefined,
        secret: secret || undefined,
        events: ["report.published", "prediction.opened"],
      }),
    onSuccess: async () => {
      setName("");
      setEndpoint("");
      setSecret("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["integrations"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const test = useMutation({
    mutationFn: (id: string) => api.testIntegration(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["integrations"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const createKey = useMutation({
    mutationFn: () => api.createApiKey({ name: keyName, scopes: ["read", "write"] }),
    onSuccess: async (row) => {
      setKeyName("");
      setCreatedSecret(row.secret);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.revokeApiKey(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Integrations & API</h1>
        <p className="mt-2 text-stone-500">
          Connect webhooks and third-party tools, and issue organization API keys.
        </p>
      </div>

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
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>Add integration</CardTitle>
          <form
            className="mt-4 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createIntegration.mutate();
            }}
          >
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="provider">Provider</Label>
              <select
                id="provider"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="webhook">Webhook</option>
                <option value="kobo">Kobo</option>
                <option value="odk">ODK</option>
                <option value="slack">Slack</option>
                <option value="sheets">Google Sheets</option>
                <option value="email">Email</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <Label htmlFor="endpoint">Endpoint URL</Label>
              <Input
                id="endpoint"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="https://hooks.example.com/impactflow"
              />
            </div>
            <div>
              <Label htmlFor="secret">Secret (optional)</Label>
              <Input
                id="secret"
                type="password"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={createIntegration.isPending}>
              {createIntegration.isPending ? "Saving…" : "Create"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Create API key</CardTitle>
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
          <div className="mt-6 space-y-2">
            {keys.data?.items.map((key) => (
              <div
                key={key.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
              >
                <div>
                  <div className="font-medium">{key.name}</div>
                  <div className="font-mono text-xs text-stone-400">{key.key_prefix}…</div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={key.status} />
                  {key.status === "active" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => revoke.mutate(key.id)}
                      disabled={revoke.isPending}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>Connections</CardTitle>
        <div className="mt-4 space-y-3">
          {integrations.data?.items.map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 px-4 py-3 dark:border-stone-800"
            >
              <div>
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-stone-400">
                  {item.provider} · {item.direction}
                  {item.endpoint_url ? ` · ${item.endpoint_url}` : ""}
                  {item.secret_hint ? ` · …${item.secret_hint}` : ""}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={item.status} />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => test.mutate(item.id)}
                  disabled={test.isPending}
                >
                  Test
                </Button>
              </div>
            </div>
          ))}
          {(integrations.data?.items.length ?? 0) === 0 && (
            <p className="text-sm text-stone-400">No integrations yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
