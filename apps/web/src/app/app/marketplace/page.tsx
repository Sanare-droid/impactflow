"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";

export default function MarketplacePage() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const apps = useQuery({
    queryKey: ["marketplace-apps"],
    queryFn: () => api.listMarketplaceApps(),
  });
  const installs = useQuery({
    queryKey: ["marketplace-installs"],
    queryFn: () => api.listMarketplaceInstallations(),
  });

  const installedAppIds = new Set(
    (installs.data?.items ?? [])
      .filter((i) => i.status === "installed")
      .map((i) => i.app_id)
  );

  const install = useMutation({
    mutationFn: (appId: string) => api.installMarketplaceApp({ app_id: appId }),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["marketplace-installs"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const uninstall = useMutation({
    mutationFn: (installationId: string) =>
      api.updateMarketplaceInstallation(installationId, { status: "uninstalled" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["marketplace-installs"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Marketplace</h1>
        <p className="mt-2 text-stone-500">
          Install connectors and packs for data collection, alerts, analytics, and donor reporting.
        </p>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <Card>
        <CardTitle>Installed</CardTitle>
        <CardDescription>Apps active for this organization.</CardDescription>
        <div className="mt-4 space-y-3">
          {(installs.data?.items ?? [])
            .filter((i) => i.status === "installed")
            .map((item) => {
              const app = apps.data?.items.find((a) => a.id === item.app_id);
              return (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 px-4 py-3 dark:border-stone-800"
                >
                  <div>
                    <div className="font-medium">{app?.name ?? item.app_id}</div>
                    <div className="text-xs text-stone-400">{app?.code}</div>
                  </div>
                  <Button
                    variant="secondary"
                    onClick={() => uninstall.mutate(item.id)}
                    disabled={uninstall.isPending}
                  >
                    Uninstall
                  </Button>
                </div>
              );
            })}
          {(installs.data?.items ?? []).filter((i) => i.status === "installed").length === 0 && (
            <p className="text-sm text-stone-400">No apps installed yet.</p>
          )}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {apps.data?.items.map((app) => {
          const isInstalled = installedAppIds.has(app.id);
          return (
            <Card key={app.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <CardTitle>{app.name}</CardTitle>
                <div className="flex gap-2">
                  {app.is_featured && <StatusBadge status="featured" />}
                  <StatusBadge status={app.pricing_tier} />
                </div>
              </div>
              <CardDescription className="mt-2">{app.summary}</CardDescription>
              <p className="mt-3 text-xs text-stone-400">
                {app.category} · {app.publisher}
              </p>
              <div className="mt-4">
                <Button
                  disabled={isInstalled || install.isPending}
                  onClick={() => install.mutate(app.id)}
                >
                  {isInstalled ? "Installed" : "Install"}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
