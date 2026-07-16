"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Smartphone, RefreshCw, Upload, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";

function formatWhen(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FieldOperationsPage() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const metricsQuery = useQuery({
    queryKey: ["field-ops-metrics"],
    queryFn: () => api.fieldOpsMetrics(),
  });

  const devicesQuery = useQuery({
    queryKey: ["field-devices"],
    queryFn: () => api.listFieldDevices(),
  });

  const sessionsQuery = useQuery({
    queryKey: ["sync-sessions"],
    queryFn: () => api.listSyncSessions(),
  });

  const mediaQuery = useQuery({
    queryKey: ["media-uploads"],
    queryFn: () => api.listMediaUploads({ status: "pending" }),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.updateFieldDeviceStatus(id, "revoked"),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["field-devices"] });
      await qc.invalidateQueries({ queryKey: ["field-ops-metrics"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.updateFieldDeviceStatus(id, "deactivated"),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["field-devices"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const metrics = metricsQuery.data;
  const devices = devicesQuery.data?.items ?? [];
  const sessions = sessionsQuery.data?.items ?? [];
  const pendingMedia = mediaQuery.data?.items ?? [];

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Field Operations
        </h1>
        <p className="mt-2 text-stone-500">
          Monitor registered devices, sync activity, and pending media uploads from the field app.
        </p>
      </div>

      {metrics && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard icon={Smartphone} label="Active devices" value={metrics.active_devices} />
          <MetricCard icon={RefreshCw} label="Sync sessions" value={metrics.sync_sessions} />
          <MetricCard icon={AlertTriangle} label="Failed mutations" value={metrics.failed_mutations} />
          <MetricCard icon={Upload} label="Conflicts logged" value={metrics.conflicts} />
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </p>
      )}

      <Card>
        <CardTitle>Registered devices</CardTitle>
        <CardDescription className="mt-1">
          Field officers register devices on login. Deactivate or revoke to force re-registration.
        </CardDescription>
        <div className="mt-4 space-y-3">
          {devicesQuery.isLoading && <p className="text-sm text-stone-500">Loading devices…</p>}
          {!devicesQuery.isLoading && devices.length === 0 && (
            <EmptyState
              title="No devices yet"
              description="Devices appear here when field officers sign in on the mobile app."
            />
          )}
          {devices.map((device) => (
            <div
              key={device.id}
              className="flex flex-col gap-3 rounded-xl border border-stone-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-stone-900">{device.name}</p>
                  <StatusBadge status={device.status} />
                  <span className="text-xs uppercase tracking-wide text-stone-400">
                    {device.platform}
                  </span>
                </div>
                <p className="mt-1 text-sm text-stone-500">
                  v{device.app_version ?? "—"} · Last seen {formatWhen(device.last_seen_at)} · Last
                  sync {formatWhen(device.last_sync_at)}
                </p>
                <p className="text-xs text-stone-400">
                  Storage {formatBytes(device.storage_bytes)} · Pending uploads{" "}
                  {device.pending_uploads}
                </p>
              </div>
              {device.status === "active" && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={deactivate.isPending}
                    onClick={() => deactivate.mutate(device.id)}
                  >
                    Deactivate
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(device.id)}
                  >
                    Revoke
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>Recent sync sessions</CardTitle>
          <CardDescription className="mt-1">Push/pull runs from field devices.</CardDescription>
          <div className="mt-4 space-y-2">
            {sessionsQuery.isLoading && (
              <p className="text-sm text-stone-500">Loading sync history…</p>
            )}
            {!sessionsQuery.isLoading && sessions.length === 0 && (
              <p className="text-sm text-stone-500">No sync sessions recorded yet.</p>
            )}
            {sessions.slice(0, 8).map((session) => (
              <div
                key={session.id}
                className="rounded-lg border border-stone-100 bg-stone-50/80 px-3 py-2 text-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <StatusBadge status={session.status} />
                  <span className="text-xs text-stone-400">{formatWhen(session.started_at)}</span>
                </div>
                <p className="mt-1 text-stone-600">
                  ↑ {session.pushed_count} pushed · ↓ {session.pulled_count} pulled
                  {session.failed_count > 0 && (
                    <span className="text-rose-600"> · {session.failed_count} failed</span>
                  )}
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>Pending media uploads</CardTitle>
          <CardDescription className="mt-1">
            Photos, signatures, and documents queued from the field.
          </CardDescription>
          <div className="mt-4 space-y-2">
            {mediaQuery.isLoading && (
              <p className="text-sm text-stone-500">Loading media queue…</p>
            )}
            {!mediaQuery.isLoading && pendingMedia.length === 0 && (
              <p className="text-sm text-stone-500">No pending uploads.</p>
            )}
            {pendingMedia.slice(0, 8).map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-stone-100 bg-stone-50/80 px-3 py-2 text-sm"
              >
                <p className="font-medium text-stone-800">{item.file_name}</p>
                <p className="text-stone-500">
                  {item.entity_type} · {formatBytes(item.file_size)}
                  {item.mime_type ? ` · ${item.mime_type}` : ""}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 text-stone-500">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-2 font-display text-2xl font-semibold text-stone-900">{value}</p>
    </Card>
  );
}
