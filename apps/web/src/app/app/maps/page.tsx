"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

type GeoPoint = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  layer: string;
};

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

  const points = useMemo(
    () =>
      (data?.items ?? []).flatMap((layer) =>
        (layer.features ?? [])
          .filter((f) => f.latitude != null && f.longitude != null)
          .map((f) => ({
            id: f.id,
            name: f.name,
            lat: Number(f.latitude),
            lng: Number(f.longitude),
            layer: layer.name,
          })),
      ),
    [data],
  );

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Geo registry
        </h1>
        <p className="mt-2 text-stone-500">
          Site and coverage layers with point features on an OpenStreetMap basemap.
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
        <CardTitle>Map</CardTitle>
        <CardDescription>
          OpenStreetMap tiles with registered site markers. © OpenStreetMap contributors.
        </CardDescription>
        <TileMap points={points} />
      </Card>

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

function lng2tile(lng: number, zoom: number) {
  return ((lng + 180) / 360) * 2 ** zoom;
}

function lat2tile(lat: number, zoom: number) {
  const rad = (lat * Math.PI) / 180;
  return (
    ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * 2 ** zoom
  );
}

function TileMap({ points }: { points: GeoPoint[] }) {
  const zoom = 6;
  const tileSize = 256;
  const viewW = 640;
  const viewH = 360;

  const center = useMemo(() => {
    if (points.length === 0) return { lat: -1.2921, lng: 36.8219 }; // Nairobi default
    return {
      lat: points.reduce((s, p) => s + p.lat, 0) / points.length,
      lng: points.reduce((s, p) => s + p.lng, 0) / points.length,
    };
  }, [points]);

  const centerTileX = lng2tile(center.lng, zoom);
  const centerTileY = lat2tile(center.lat, zoom);
  const originX = centerTileX * tileSize - viewW / 2;
  const originY = centerTileY * tileSize - viewH / 2;

  const minTX = Math.floor(originX / tileSize);
  const maxTX = Math.floor((originX + viewW) / tileSize);
  const minTY = Math.floor(originY / tileSize);
  const maxTY = Math.floor((originY + viewH) / tileSize);

  const tiles: Array<{ x: number; y: number; left: number; top: number }> = [];
  for (let x = minTX; x <= maxTX; x++) {
    for (let y = minTY; y <= maxTY; y++) {
      if (y < 0 || y >= 2 ** zoom) continue;
      tiles.push({
        x: ((x % 2 ** zoom) + 2 ** zoom) % 2 ** zoom,
        y,
        left: x * tileSize - originX,
        top: y * tileSize - originY,
      });
    }
  }

  return (
    <div
      className="relative mt-4 overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800"
      style={{ height: viewH }}
    >
      <div className="absolute inset-0 bg-stone-100 dark:bg-stone-900">
        {tiles.map((t) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={`${t.x}-${t.y}`}
            alt=""
            draggable={false}
            className="pointer-events-none absolute"
            style={{ left: t.left, top: t.top, width: tileSize, height: tileSize }}
            src={`https://tile.openstreetmap.org/${zoom}/${t.x}/${t.y}.png`}
          />
        ))}
      </div>
      {points.map((p) => {
        const px = lng2tile(p.lng, zoom) * tileSize - originX;
        const py = lat2tile(p.lat, zoom) * tileSize - originY;
        return (
          <div
            key={p.id}
            title={`${p.name} (${p.layer})`}
            className="absolute z-10 -translate-x-1/2 -translate-y-full"
            style={{ left: px, top: py }}
          >
            <span className="block h-3 w-3 rounded-full border-2 border-white bg-teal-700 shadow" />
          </div>
        );
      })}
      {points.length === 0 && (
        <p className="absolute inset-x-0 bottom-3 z-10 text-center text-sm text-stone-600">
          Add latitude/longitude features to plot markers on the basemap.
        </p>
      )}
    </div>
  );
}
