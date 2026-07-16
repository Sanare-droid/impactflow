"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  Check,
  Copy,
  Download,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Star,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { api, type AiMessage, type AiStreamEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MarkdownMessage } from "@/components/ai/MarkdownMessage";
import { CitationChips } from "@/components/ai/CitationChips";
import { cn } from "@/lib/utils";

export default function CopilotPage() {
  const qc = useQueryClient();
  const pathname = usePathname();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [streamText, setStreamText] = useState("");
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const threadRef = useRef<HTMLDivElement>(null);

  const conversations = useQuery({
    queryKey: ["ai-conversations"],
    queryFn: () => api.listAiConversations(),
  });

  const detail = useQuery({
    queryKey: ["ai-conversation", activeId],
    queryFn: () => api.getAiConversation(activeId!),
    enabled: !!activeId,
  });

  const suggested = useQuery({
    queryKey: ["ai-suggested-questions"],
    queryFn: () => api.suggestedQuestions(),
    staleTime: 5 * 60 * 1000,
  });

  const items = useMemo(
    () =>
      (conversations.data?.items ?? []).filter((c) => c.status !== "archived"),
    [conversations.data],
  );
  const pinned = useMemo(() => items.filter((c) => c.pinned), [items]);
  const recent = useMemo(() => items.filter((c) => !c.pinned), [items]);

  const messages = detail.data?.messages ?? [];
  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return messages[i].id;
    }
    return null;
  }, [messages]);

  const busy = isStreaming || detail.isFetching;

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, streamText, pendingUser, activeTools.length]);

  async function runTurn(text: string) {
    if (!text.trim() || isStreaming) return;
    setError(null);
    setInput("");

    let id = activeId;
    if (!id) {
      try {
        const conv = await api.createAiConversation({ title: "New conversation" });
        id = conv.id;
        setActiveId(id);
        await qc.invalidateQueries({ queryKey: ["ai-conversations"] });
      } catch (e) {
        setError((e as Error).message);
        return;
      }
    }

    const pageContext = { path: pathname };
    setPendingUser(text);
    setStreamText("");
    setActiveTools([]);
    setIsStreaming(true);

    let finished = false;
    let streamError: string | null = null;

    const onEvent = (ev: AiStreamEvent) => {
      switch (ev.event) {
        case "token":
          setStreamText((prev) => prev + ev.text);
          break;
        case "tool_start":
          setActiveTools((prev) =>
            prev.includes(ev.tool) ? prev : [...prev, ev.tool],
          );
          break;
        case "done":
          finished = true;
          break;
        case "error":
          streamError = ev.detail || ev.error;
          break;
      }
    };

    try {
      await api.streamAiMessage(id, text, onEvent, pageContext);
    } catch {
      // Streaming unavailable — fall back to the blocking endpoint.
      try {
        await api.sendAiMessage(id, text, pageContext);
        finished = true;
      } catch (e) {
        setError((e as Error).message);
      }
    }

    if (!finished && streamError) setError(streamError);

    setIsStreaming(false);
    setPendingUser(null);
    setStreamText("");
    setActiveTools([]);
    await qc.invalidateQueries({ queryKey: ["ai-conversation", id] });
    await qc.invalidateQueries({ queryKey: ["ai-conversations"] });
    await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  }

  const pinToggle = useMutation({
    mutationFn: (c: { id: string; pinned: boolean }) =>
      api.updateAiConversation(c.id, { pinned: !c.pinned }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-conversations"] }),
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.archiveAiConversation(id),
    onSuccess: async (_data, id) => {
      if (activeId === id) setActiveId(null);
      await qc.invalidateQueries({ queryKey: ["ai-conversations"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });

  const feedback = useMutation({
    mutationFn: (v: { messageId: string; value: "up" | "down" }) =>
      api.messageFeedback(v.messageId, v.value),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["ai-conversation", activeId] }),
  });

  const regenerate = useMutation({
    mutationFn: () => api.regenerateAiMessage(activeId!),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["ai-conversation", activeId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  async function handleCopy(message: AiMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.id);
      setTimeout(() => setCopiedId((c) => (c === message.id ? null : c)), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  async function handleExport() {
    if (!activeId) return;
    try {
      const md = await api.exportAiConversation(activeId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `conversation-${activeId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const suggestions = suggested.data?.questions ?? [];

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700/80 dark:text-teal-300/80">
          AI Copilot
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">
          Ask ImpactFlow
        </h1>
        <p className="mt-2 max-w-2xl text-stone-500">
          Grounded in your portfolio data and knowledge base. Ask about delivery
          risk, MEAL gaps, and donor-ready next steps.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[288px_1fr]">
        {/* Left rail */}
        <div className="space-y-4">
          <Button
            type="button"
            className="w-full"
            onClick={() => {
              setActiveId(null);
              setError(null);
            }}
          >
            <Plus className="h-4 w-4" /> New chat
          </Button>

          {suggestions.length > 0 && (
            <Card className="p-4">
              <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
                <Sparkles className="h-3.5 w-3.5" /> Suggested
              </p>
              <div className="mt-3 space-y-1.5">
                {suggestions.slice(0, 4).map((q) => (
                  <button
                    key={q}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => runTurn(q)}
                    className="block w-full rounded-lg border border-stone-200 px-2.5 py-1.5 text-left text-xs text-stone-600 transition-colors hover:border-teal-300 hover:text-teal-800 disabled:opacity-50 dark:border-stone-700 dark:text-stone-300 dark:hover:text-teal-300"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </Card>
          )}

          {pinned.length > 0 && (
            <Card className="p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Pinned
              </p>
              <div className="mt-2 space-y-1">
                {pinned.map((c) => (
                  <ConversationRow
                    key={c.id}
                    title={c.title}
                    active={activeId === c.id}
                    pinned
                    onSelect={() => setActiveId(c.id)}
                    onPin={() => pinToggle.mutate({ id: c.id, pinned: true })}
                    onArchive={() => archive.mutate(c.id)}
                  />
                ))}
              </div>
            </Card>
          )}

          <Card className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Recent
            </p>
            <div className="mt-2 space-y-1">
              {recent.map((c) => (
                <ConversationRow
                  key={c.id}
                  title={c.title}
                  active={activeId === c.id}
                  pinned={false}
                  onSelect={() => setActiveId(c.id)}
                  onPin={() => pinToggle.mutate({ id: c.id, pinned: false })}
                  onArchive={() => archive.mutate(c.id)}
                />
              ))}
              {!conversations.isLoading && recent.length === 0 && (
                <p className="px-1 py-2 text-xs text-stone-400">
                  No conversations yet.
                </p>
              )}
            </div>
          </Card>
        </div>

        {/* Main thread */}
        <Card className="flex min-h-[560px] flex-col p-0">
          <div className="flex items-center justify-between gap-3 border-b border-stone-200 px-5 py-4 dark:border-stone-800">
            <div className="min-w-0">
              <p className="truncate font-display text-base font-semibold tracking-tight text-stone-900 dark:text-stone-50">
                {detail.data?.title ?? "New chat"}
              </p>
              <p className="text-xs text-stone-400">
                Grounded with knowledge snippets and portfolio snapshot.
              </p>
            </div>
            {activeId && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleExport}
              >
                <Download className="h-3.5 w-3.5" /> Export
              </Button>
            )}
          </div>

          <div
            ref={threadRef}
            className="flex-1 space-y-4 overflow-y-auto px-5 py-5"
          >
            {!activeId && !pendingUser && (
              <div className="flex h-full flex-col items-center justify-center py-10 text-center">
                <div className="rounded-2xl bg-teal-50 p-3 text-teal-700 dark:bg-teal-950 dark:text-teal-300">
                  <Sparkles className="h-6 w-6" />
                </div>
                <p className="mt-4 font-display text-lg font-semibold tracking-tight text-stone-900 dark:text-stone-50">
                  How can I help today?
                </p>
                <p className="mt-1 max-w-md text-sm text-stone-500">
                  Ask a question below, or start with one of these.
                </p>
                <div className="mt-5 flex max-w-lg flex-wrap justify-center gap-2">
                  {suggestions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      disabled={isStreaming}
                      onClick={() => runTurn(q)}
                      className="rounded-full border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-teal-300 hover:text-teal-800 disabled:opacity-50 dark:border-stone-700 dark:text-stone-300 dark:hover:text-teal-300"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                copied={copiedId === m.id}
                onCopy={() => handleCopy(m)}
                onFeedback={(value) =>
                  feedback.mutate({ messageId: m.id, value })
                }
                isLastAssistant={m.id === lastAssistantId}
                onRegenerate={() => regenerate.mutate()}
                regenerating={regenerate.isPending}
              />
            ))}

            {pendingUser && (
              <div className="ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-teal-700 px-4 py-3 text-sm text-white">
                <p className="whitespace-pre-wrap">{pendingUser}</p>
              </div>
            )}

            {isStreaming && (
              <div className="mr-auto max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3 dark:bg-stone-900">
                {activeTools.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {activeTools.map((t) => (
                      <span
                        key={t}
                        className="rounded-full bg-stone-200 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-600 dark:bg-stone-800 dark:text-stone-300"
                      >
                        {t.replaceAll("_", " ")}
                      </span>
                    ))}
                  </div>
                )}
                {streamText ? (
                  <MarkdownMessage
                    content={streamText}
                    className="text-stone-800 dark:text-stone-100"
                  />
                ) : (
                  <TypingIndicator />
                )}
              </div>
            )}
          </div>

          <form
            className="border-t border-stone-200 px-5 py-4 dark:border-stone-800"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              runTurn(input);
            }}
          >
            {error && (
              <p className="mb-2 text-sm text-rose-600 dark:text-rose-400">
                {error}
              </p>
            )}
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    runTurn(input);
                  }
                }}
                rows={1}
                placeholder="Ask about delivery risk, MEAL gaps, donor reports…"
                className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 shadow-sm transition-colors placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100"
              />
              <Button
                type="submit"
                size="icon"
                disabled={busy || !input.trim()}
                className="h-11 w-11 shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

function ConversationRow({
  title,
  active,
  pinned,
  onSelect,
  onPin,
  onArchive,
}: {
  title: string;
  active: boolean;
  pinned: boolean;
  onSelect: () => void;
  onPin: () => void;
  onArchive: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex items-center gap-1 rounded-lg pr-1 transition-colors",
        active
          ? "bg-teal-50 dark:bg-teal-950/40"
          : "hover:bg-stone-100 dark:hover:bg-stone-900",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "flex-1 truncate px-2.5 py-2 text-left text-sm",
          active
            ? "font-medium text-teal-900 dark:text-teal-100"
            : "text-stone-700 dark:text-stone-300",
        )}
      >
        {title}
      </button>
      <button
        type="button"
        onClick={onPin}
        title={pinned ? "Unpin" : "Pin"}
        className={cn(
          "rounded-md p-1 text-stone-400 opacity-0 transition-opacity hover:text-amber-500 group-hover:opacity-100",
          pinned && "text-amber-500 opacity-100",
        )}
      >
        <Star className={cn("h-3.5 w-3.5", pinned && "fill-current")} />
      </button>
      <button
        type="button"
        onClick={onArchive}
        title="Archive"
        className="rounded-md p-1 text-stone-400 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
      >
        <Archive className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function MessageBubble({
  message,
  copied,
  onCopy,
  onFeedback,
  isLastAssistant,
  onRegenerate,
  regenerating,
}: {
  message: AiMessage;
  copied: boolean;
  onCopy: () => void;
  onFeedback: (value: "up" | "down") => void;
  isLastAssistant: boolean;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  const isUser = message.role === "user";
  const feedbackValue = message.metadata?.feedback;

  if (isUser) {
    return (
      <div className="ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-teal-700 px-4 py-3 text-sm text-white">
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    );
  }

  return (
    <div className="mr-auto max-w-[85%]">
      <div className="rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3 text-stone-800 dark:bg-stone-900 dark:text-stone-100">
        <MarkdownMessage content={message.content} />
        <CitationChips citations={message.metadata?.citations} />
      </div>
      <div className="mt-1.5 flex items-center gap-1 px-1 text-stone-400">
        <button
          type="button"
          onClick={onCopy}
          title="Copy"
          className="rounded-md p-1 transition-colors hover:text-stone-700 dark:hover:text-stone-200"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
        <button
          type="button"
          onClick={() => onFeedback("up")}
          title="Helpful"
          className={cn(
            "rounded-md p-1 transition-colors hover:text-emerald-600",
            feedbackValue === "up" && "text-emerald-600",
          )}
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onFeedback("down")}
          title="Not helpful"
          className={cn(
            "rounded-md p-1 transition-colors hover:text-rose-600",
            feedbackValue === "down" && "text-rose-600",
          )}
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>
        {isLastAssistant && (
          <button
            type="button"
            onClick={onRegenerate}
            disabled={regenerating}
            title="Regenerate"
            className="rounded-md p-1 transition-colors hover:text-teal-700 disabled:opacity-50 dark:hover:text-teal-300"
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5", regenerating && "animate-spin")}
            />
          </button>
        )}
        {message.provider && (
          <span className="ml-1 text-[11px]">
            {message.provider}
            {message.model ? ` · ${message.model}` : ""}
          </span>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 animate-bounce rounded-full bg-stone-400 dark:bg-stone-500"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
