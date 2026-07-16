"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function CopilotPage() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const conversations = useQuery({
    queryKey: ["ai-conversations"],
    queryFn: () => api.listAiConversations(),
  });

  const detail = useQuery({
    queryKey: ["ai-conversation", activeId],
    queryFn: () => api.getAiConversation(activeId!),
    enabled: !!activeId,
  });

  const create = useMutation({
    mutationFn: () => api.createAiConversation({ title: "New conversation" }),
    onSuccess: async (conv) => {
      setActiveId(conv.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["ai-conversations"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const send = useMutation({
    mutationFn: async () => {
      let id = activeId;
      if (!id) {
        const conv = await api.createAiConversation({ title: "New conversation" });
        id = conv.id;
        setActiveId(id);
      }
      const detail = await api.sendAiMessage(id, message);
      return detail;
    },
    onSuccess: async (detail) => {
      setMessage("");
      setError(null);
      setActiveId(detail.id);
      await qc.invalidateQueries({ queryKey: ["ai-conversations"] });
      await qc.invalidateQueries({ queryKey: ["ai-conversation", detail.id] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">AI Copilot</h1>
        <p className="mt-2 text-stone-500">
          Ask about delivery risk, MEAL gaps, and donor-ready next steps. Uses OpenAI when
          configured; otherwise a deterministic fallback.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Card>
          <CardTitle>Conversations</CardTitle>
          <CardDescription>Your copilot threads for this organization.</CardDescription>
          <div className="mt-4 space-y-2">
            <Button type="button" onClick={() => create.mutate()} disabled={create.isPending}>
              {create.isPending ? "Starting…" : "New chat"}
            </Button>
            {conversations.data?.items.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setActiveId(c.id)}
                className={`block w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                  activeId === c.id
                    ? "bg-teal-50 text-teal-900 dark:bg-teal-950/40 dark:text-teal-100"
                    : "hover:bg-stone-100 dark:hover:bg-stone-900"
                }`}
              >
                <div className="font-medium">{c.title}</div>
                <div className="text-xs text-stone-400">{c.status}</div>
              </button>
            ))}
            {!conversations.isLoading && (conversations.data?.items.length ?? 0) === 0 && (
              <p className="text-sm text-stone-400">No conversations yet.</p>
            )}
          </div>
        </Card>

        <Card className="flex min-h-[480px] flex-col">
          <CardTitle>{detail.data?.title ?? "Chat"}</CardTitle>
          <CardDescription>
            Grounded with knowledge-base snippets and portfolio snapshot counts.
          </CardDescription>
          <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
            {(detail.data?.messages ?? []).map((m) => (
              <div
                key={m.id}
                className={`rounded-2xl px-4 py-3 text-sm ${
                  m.role === "user"
                    ? "ml-8 bg-teal-700 text-white"
                    : "mr-8 bg-stone-100 text-stone-800 dark:bg-stone-900 dark:text-stone-100"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && (
                  <p className="mt-2 text-[11px] opacity-70">
                    {m.provider}
                    {m.model ? ` · ${m.model}` : ""}
                  </p>
                )}
              </div>
            ))}
            {!activeId && (
              <p className="text-sm text-stone-400">
                Start a conversation or select an existing thread.
              </p>
            )}
          </div>
          <form
            className="mt-4 space-y-3 border-t border-stone-200 pt-4 dark:border-stone-800"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (!message.trim()) return;
              send.mutate();
            }}
          >
            <div>
              <Label htmlFor="message">Message</Label>
              <Input
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What delivery risks should we watch this month?"
              />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <Button type="submit" disabled={send.isPending || !message.trim()}>
              {send.isPending ? "Thinking…" : "Send"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
