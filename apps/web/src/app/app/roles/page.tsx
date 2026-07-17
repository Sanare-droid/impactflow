"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function RolesPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editId, setEditId] = useState<string | null>(null);

  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.roles(),
  });
  const { data: permissions } = useQuery({
    queryKey: ["permissions"],
    queryFn: () => api.listPermissions(),
  });

  const permOptions = useMemo(() => permissions ?? [], [permissions]);

  const create = useMutation({
    mutationFn: () =>
      api.createRole({
        name,
        description: description || undefined,
        permissions: selectedPerms,
      }),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setSelectedPerms([]);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const update = useMutation({
    mutationFn: () => {
      if (!editId) throw new Error("No role selected");
      return api.updateRole(editId, {
        description: description || undefined,
        permissions: selectedPerms,
      });
    },
    onSuccess: async () => {
      setEditId(null);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  function togglePerm(code: string) {
    setSelectedPerms((prev) =>
      prev.includes(code) ? prev.filter((p) => p !== code) : [...prev, code],
    );
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Roles</h1>
        <p className="mt-2 text-stone-500">
          System roles plus custom roles with granular permissions.
        </p>
      </div>

      {loadError && (
        <Card className="border-rose-200 text-rose-700">
          {(loadError as Error).message}
        </Card>
      )}

      <Card>
        <CardTitle>{editId ? "Edit custom role" : "Create custom role"}</CardTitle>
        <CardDescription>
          Pick permissions from the catalog. System roles stay read-only.
        </CardDescription>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (editId) update.mutate();
            else create.mutate();
          }}
        >
          {!editId ? (
            <div>
              <Label htmlFor="role-name">Name</Label>
              <Input
                id="role-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          ) : null}
          <div>
            <Label htmlFor="role-desc">Description</Label>
            <Input
              id="role-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div>
            <Label>Permissions</Label>
            <div className="mt-2 max-h-48 overflow-y-auto rounded-xl border border-stone-200 p-3 dark:border-stone-800">
              <div className="flex flex-wrap gap-2">
                {permOptions.slice(0, 80).map((p) => (
                  <button
                    key={p.code}
                    type="button"
                    onClick={() => togglePerm(p.code)}
                    className={`rounded-md px-2 py-1 text-xs ${
                      selectedPerms.includes(p.code)
                        ? "bg-teal-700 text-white"
                        : "bg-stone-100 text-stone-700 dark:bg-stone-900 dark:text-stone-300"
                    }`}
                  >
                    {p.code}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={create.isPending || update.isPending}>
              {editId
                ? update.isPending
                  ? "Saving…"
                  : "Save role"
                : create.isPending
                  ? "Creating…"
                  : "Create role"}
            </Button>
            {editId ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setEditId(null);
                  setSelectedPerms([]);
                  setDescription("");
                }}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        </form>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {isLoading && <Card>Loading roles…</Card>}
        {data?.map((role) => (
          <Card key={role.id}>
            <CardTitle>{role.name}</CardTitle>
            <CardDescription>{role.description}</CardDescription>
            <p className="mt-2 text-xs text-stone-500">
              {role.is_system ? "System role" : "Custom role"} · {role.slug}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {role.permissions.slice(0, 8).map((p) => (
                <span
                  key={p}
                  className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700 dark:bg-stone-900 dark:text-stone-300"
                >
                  {p}
                </span>
              ))}
              {role.permissions.length > 8 && (
                <span className="text-xs text-stone-500">
                  +{role.permissions.length - 8} more
                </span>
              )}
            </div>
            {!role.is_system ? (
              <Button
                className="mt-4"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setEditId(role.id);
                  setDescription(role.description ?? "");
                  setSelectedPerms(role.permissions);
                }}
              >
                Edit
              </Button>
            ) : null}
          </Card>
        ))}
      </div>
    </div>
  );
}
