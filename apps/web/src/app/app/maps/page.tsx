"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function MapsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [layerType, setLayerType] = useState("sites");
  const [layerId, setLayerId] = useState("");
  const [featureName, setFeatureName] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["map-layers"],
    queryFn: () => api.listMapLayers(),
  });

  const createLayer = useMutation({
    mutationFn: () =>
      api.createMapLayer({
        name,
        layer_type: layerType,
        status: "active",
      }),
    onSuccess: async () => {
      setName("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["map-layers"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const addFeature = useMutation({
    mutationFn: () =>
      api.addMapFeature(layerId, {
        name: featureName,
        feature_type: "point",
        latitude: lat ? Number(lat) : undefined,
        longitude: lng ? Number(lng) : undefined,
      }),
    onSuccess: async () => {
      setFeatureName("");
      setLat("");
      setLng("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["map-layers"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Maps</h1>
        <p className="mt-2 text-stone-500">
          Site and coverage layers with point features for field geography.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>New layer</CardTitle>
          <CardDescription>Group map features by theme.</CardDescription>
          <form
            className="mt-4 grid gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createLayer.mutate();
            }}
          >
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="type">Type</Label>
              <select
                id="type"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={layerType}
                onChange={(e) => setLayerType(e.target.value)}
              >
                <option value="sites">Sites</option>
                <option value="coverage">Coverage</option>
                <option value="communities">Communities</option>
                <option value="hazards">Hazards</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <Button type="submit" disabled={createLayer.isPending}>
              {createLayer.isPending ? "Saving…" : "Create layer"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardTitle>Add point feature</CardTitle>
          <CardDescription>Latitude / longitude site marker.</CardDescription>
          <form
            className="mt-4 grid gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              addFeature.mutate();
            }}
          >
            <div>
              <Label htmlFor="layer">Layer</Label>
              <select
                id="layer"
                required
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={layerId}
                onChange={(e) => setLayerId(e.target.value)}
              >
                <option value="">Select…</option>
                {data?.items.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="fname">Feature name</Label>
              <Input
                id="fname"
                required
                value={featureName}
                onChange={(e) => setFeatureName(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="lat">Latitude</Label>
                <Input id="lat" value={lat} onChange={(e) => setLat(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="lng">Longitude</Label>
                <Input id="lng" value={lng} onChange={(e) => setLng(e.target.value)} />
              </div>
            </div>
            <Button type="submit" disabled={addFeature.isPending || !layerId}>
              {addFeature.isPending ? "Saving…" : "Add feature"}
            </Button>
          </form>
        </Card>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <Card>
        <CardTitle>Map layers</CardTitle>
        <div className="mt-4 space-y-5">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {data?.items.map((layer) => (
            <div
              key={layer.id}
              className="border-b border-stone-100 pb-4 last:border-0 dark:border-stone-900"
            >
              <div className="flex flex-wrap items-center gap-3">
                <p className="font-medium">{layer.name}</p>
                <span className="font-mono text-xs text-stone-500">{layer.code}</span>
                <StatusBadge status={layer.status} />
                <span className="text-xs capitalize text-stone-500">{layer.layer_type}</span>
              </div>
              <ul className="mt-3 space-y-1 text-sm text-stone-600 dark:text-stone-300">
                {(layer.features ?? []).length === 0 && (
                  <li className="text-stone-400">No features yet.</li>
                )}
                {(layer.features ?? []).map((f) => (
                  <li key={f.id}>
                    {f.name}
                    {f.latitude != null && f.longitude != null
                      ? ` · ${f.latitude}, ${f.longitude}`
                      : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
