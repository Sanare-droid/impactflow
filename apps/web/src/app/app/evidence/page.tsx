"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function EvidencePage() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [evidenceType, setEvidenceType] = useState("document");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["evidence"],
    queryFn: () => api.listEvidence(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createEvidence({
        title,
        evidence_type: evidenceType,
        source: source || undefined,
        status: "submitted",
      }),
    onSuccess: async () => {
      setTitle("");
      setSource("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["evidence"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.updateEvidence(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidence"] }),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Evidence</h1>
        <p className="mt-2 text-stone-500">
          Documents, photos, and case evidence linked to MEAL and delivery work.
        </p>
      </div>

      <Card>
        <CardTitle>Add evidence</CardTitle>
        <CardDescription>Register supporting material for verification.</CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="title">Title</Label>
            <Input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="type">Type</Label>
            <select
              id="type"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value)}
            >
              <option value="document">Document</option>
              <option value="photo">Photo</option>
              <option value="video">Video</option>
              <option value="survey">Survey</option>
              <option value="case_study">Case study</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="source">Source</Label>
            <Input id="source" value={source} onChange={(e) => setSource(e.target.value)} />
          </div>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Add evidence"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Evidence register</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Source</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={6}>
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (data?.items.length ?? 0) === 0 && (
                <tr>
                  <td className="py-6" colSpan={6}>
                    <EmptyState
                      title="No evidence yet"
                      description="Register documents, photos, or case materials for verification."
                      actionLabel="Add evidence"
                      actionHref="/app/evidence"
                    />
                  </td>
                </tr>
              )}
              {data?.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">{item.title}</td>
                  <td className="py-3 font-mono text-xs">{item.code}</td>
                  <td className="py-3 capitalize">{item.evidence_type.replaceAll("_", " ")}</td>
                  <td className="py-3">{item.source || "—"}</td>
                  <td className="py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="py-3">
                    <div className="flex gap-2">
                      {item.status !== "verified" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={setStatus.isPending}
                          onClick={() => setStatus.mutate({ id: item.id, status: "verified" })}
                        >
                          Verify
                        </Button>
                      )}
                      {item.status !== "rejected" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={setStatus.isPending}
                          onClick={() => setStatus.mutate({ id: item.id, status: "rejected" })}
                        >
                          Reject
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
