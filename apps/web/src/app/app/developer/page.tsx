"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Copy, Download, ExternalLink } from "lucide-react";
import { API_URL, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

function CodeBlock({ label, code }: { label: string; code: string }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50/80 dark:border-stone-800 dark:bg-stone-900/40">
      <div className="flex items-center justify-between gap-2 border-b border-stone-200 px-3 py-2 dark:border-stone-800">
        <span className="text-xs font-medium uppercase tracking-wider text-stone-400">
          {label}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void navigator.clipboard.writeText(code)}
        >
          <Copy className="h-3.5 w-3.5" />
          Copy
        </Button>
      </div>
      <pre className="overflow-x-auto p-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
        {code}
      </pre>
    </div>
  );
}

export default function DeveloperPortalPage() {
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const portal = useQuery({
    queryKey: ["developer-portal"],
    queryFn: () => api.getDeveloperPortal(),
  });

  const events = useQuery({
    queryKey: ["developer-events"],
    queryFn: () => api.listDeveloperEvents(),
  });

  const plugins = useQuery({
    queryKey: ["plugins"],
    queryFn: () => api.listPlugins(),
  });

  const data = portal.data;
  const eventItems = events.data?.items ?? data?.events ?? [];
  const connectors = data?.connectors ?? [];
  const samples = data?.code_samples ?? {};

  const downloadOpenApi = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      await api.downloadDeveloperOpenApi(
        `impactflow-openapi-${data?.api_version ?? "latest"}.json`,
      );
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Developer Portal
          </h1>
          <p className="mt-2 max-w-2xl text-stone-500">
            Authenticate against the ImpactFlow API, subscribe to platform events, explore
            connectors, and download the OpenAPI specification.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/app/integrations">
            <Button variant="secondary" size="sm">
              Integrations Hub
            </Button>
          </Link>
          <Button size="sm" onClick={() => void downloadOpenApi()} disabled={downloading}>
            <Download className="h-3.5 w-3.5" />
            {downloading ? "Downloading…" : "Download OpenAPI"}
          </Button>
        </div>
      </div>

      {portal.isLoading && (
        <p className="text-sm text-stone-400">Loading developer portal…</p>
      )}
      {portal.isError && (
        <p className="text-sm text-rose-600">
          {(portal.error as Error).message || "Failed to load portal"}
        </p>
      )}
      {downloadError && <p className="text-sm text-rose-600">{downloadError}</p>}

      {data && (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <div className="flex flex-wrap items-center gap-2">
                <BookOpen className="h-5 w-5 text-teal-700 dark:text-teal-300" />
                <CardTitle>Authentication</CardTitle>
                <StatusBadge status={`API ${data.api_version}`} />
              </div>
              <CardDescription className="mt-2">
                Prefer JWT for interactive sessions; use API keys for server-to-server and ETL.
              </CardDescription>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-stone-400">
                    JWT
                  </dt>
                  <dd className="mt-1 font-mono text-xs text-stone-700 dark:text-stone-300">
                    {data.authentication.jwt}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-stone-400">
                    API key
                  </dt>
                  <dd className="mt-1 font-mono text-xs text-stone-700 dark:text-stone-300">
                    {data.authentication.api_key}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wider text-stone-400">
                    Organization
                  </dt>
                  <dd className="mt-1 font-mono text-xs text-stone-700 dark:text-stone-300">
                    {data.authentication.organization_header}
                  </dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                <a
                  href={`${API_URL}${data.docs_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
                >
                  Interactive docs <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <a
                  href={`${API_URL}${data.openapi_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
                >
                  Raw OpenAPI <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </Card>

            <Card>
              <CardTitle>Webhooks</CardTitle>
              <CardDescription className="mt-2">
                Sign and verify outbound deliveries; accept inbound events.
              </CardDescription>
              <ul className="mt-4 space-y-2 text-sm text-stone-600 dark:text-stone-300">
                <li>
                  <span className="font-medium text-stone-800 dark:text-stone-100">
                    Outbound:
                  </span>{" "}
                  {data.webhooks.outbound}
                </li>
                <li>
                  <span className="font-medium text-stone-800 dark:text-stone-100">
                    Inbound:
                  </span>{" "}
                  <code className="text-xs">{data.webhooks.inbound}</code>
                </li>
                <li>
                  <span className="font-medium text-stone-800 dark:text-stone-100">
                    Signature:
                  </span>{" "}
                  <code className="text-xs">{data.webhooks.signing_header}</code>
                </li>
                <li>
                  <span className="font-medium text-stone-800 dark:text-stone-100">
                    Retry:
                  </span>{" "}
                  {data.webhooks.retry}
                </li>
              </ul>
            </Card>
          </div>

          <Card>
            <CardTitle>Code samples</CardTitle>
            <CardDescription>
              {data.postman?.hint ?? "Import OpenAPI into Postman or your HTTP client."}
            </CardDescription>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {Object.entries(samples).map(([key, code]) => (
                <CodeBlock key={key} label={key.replaceAll("_", " ")} code={code} />
              ))}
              {Object.keys(samples).length === 0 && (
                <p className="text-sm text-stone-400">No samples available.</p>
              )}
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardTitle>Platform events</CardTitle>
              <CardDescription>
                Subscribe via webhook integrations or the event bus.
              </CardDescription>
              <div className="mt-4 max-h-80 space-y-2 overflow-y-auto">
                {eventItems.map((ev) => (
                  <div
                    key={ev.code}
                    className="rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
                  >
                    <div className="font-mono text-xs text-teal-800 dark:text-teal-300">
                      {ev.code}
                    </div>
                    <div className="mt-0.5 text-stone-500">{ev.description}</div>
                  </div>
                ))}
                {eventItems.length === 0 && (
                  <EmptyState title="No events listed" description="Events catalog is empty." />
                )}
              </div>
            </Card>

            <Card>
              <CardTitle>Connector catalog</CardTitle>
              <CardDescription>
                {connectors.length} connectors available in the hub.
              </CardDescription>
              <div className="mt-4 max-h-80 space-y-2 overflow-y-auto">
                {connectors.map((c) => (
                  <div
                    key={c.code}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
                  >
                    <div>
                      <div className="font-medium">{c.name}</div>
                      <div className="text-xs text-stone-400">
                        {c.code} · {c.category} · {c.auth_type}
                        {c.version ? ` · v${c.version}` : ""}
                      </div>
                    </div>
                    <StatusBadge status={c.status ?? "available"} />
                  </div>
                ))}
              </div>
              <Link
                href="/app/integrations"
                className="mt-4 inline-block text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
              >
                Enable connectors in the hub →
              </Link>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardTitle>Plugins</CardTitle>
              <CardDescription>Extension points and installed manifests.</CardDescription>
              <div className="mt-4 space-y-2">
                {(plugins.data?.items ?? []).map((p) => (
                  <div
                    key={p.id}
                    className="rounded-xl border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-medium">{p.name}</div>
                      <StatusBadge status={p.status} />
                    </div>
                    <div className="mt-0.5 text-xs text-stone-400">
                      {p.code} · v{p.version}
                    </div>
                    {p.description && (
                      <p className="mt-1 text-stone-500">{p.description}</p>
                    )}
                  </div>
                ))}
                {(plugins.data?.items.length ?? 0) === 0 && !plugins.isLoading && (
                  <p className="text-sm text-stone-400">No plugins listed.</p>
                )}
              </div>
            </Card>

            <Card>
              <CardTitle>Changelog</CardTitle>
              <CardDescription>API version history relevant to integrations.</CardDescription>
              <ol className="mt-4 space-y-3">
                {(data.changelog ?? []).map((entry) => (
                  <li
                    key={entry.version}
                    className="border-l-2 border-teal-600/40 pl-3 dark:border-teal-400/40"
                  >
                    <div className="font-mono text-sm font-medium text-stone-800 dark:text-stone-100">
                      {entry.version}
                    </div>
                    <p className="mt-0.5 text-sm text-stone-500">{entry.notes}</p>
                  </li>
                ))}
              </ol>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
