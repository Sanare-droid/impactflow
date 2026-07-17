"use client";

import { FeatureGate } from "@/components/feature-gate";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function KnowledgePage() {
  return (
    <FeatureGate feature="ai" fallbackTitle="Knowledge requires Starter+">
      <KnowledgeInner />
    </FeatureGate>
  );
}

function KnowledgeInner() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("guidance");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge"],
    queryFn: () => api.listKnowledge(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createKnowledge({
        name,
        category,
        summary: summary || undefined,
        content,
        status: "published",
      }),
    onSuccess: async () => {
      setName("");
      setSummary("");
      setContent("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["knowledge"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Knowledge Base</h1>
        <p className="mt-2 text-stone-500">
          SOPs, guidance, and lessons that ground the AI Copilot for your organization.
        </p>
      </div>

      <Card>
        <CardTitle>Add document</CardTitle>
        <CardDescription>Published articles are searchable by the copilot.</CardDescription>
        <form
          className="mt-4 grid gap-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <Label htmlFor="name">Title</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="category">Category</Label>
              <select
                id="category"
                className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="guidance">Guidance</option>
                <option value="sop">SOP</option>
                <option value="lessons">Lessons</option>
                <option value="policy">Policy</option>
                <option value="faq">FAQ</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="summary">Summary</Label>
            <Input id="summary" value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="content">Content</Label>
            <textarea
              id="content"
              required
              rows={6}
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Publish"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Documents</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Category</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={4}>
                    Loading…
                  </td>
                </tr>
              )}
              {data?.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3">
                    <div className="font-medium">{item.name}</div>
                    {item.summary && (
                      <div className="mt-1 text-xs text-stone-400">{item.summary}</div>
                    )}
                  </td>
                  <td className="py-3 font-mono text-xs">{item.code}</td>
                  <td className="py-3">{item.category}</td>
                  <td className="py-3">
                    <StatusBadge status={item.status} />
                  </td>
                </tr>
              ))}
              {!isLoading && (data?.items.length ?? 0) === 0 && (
                <tr>
                  <td className="py-4 text-stone-400" colSpan={4}>
                    No knowledge documents yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
