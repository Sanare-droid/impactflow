"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";

export default function NotificationsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.listNotifications(),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Notifications
          </h1>
          <p className="mt-2 text-stone-500">
            Alerts for predictions, reports, invites, and overdue work.
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={markAll.isPending}
          onClick={() => markAll.mutate()}
        >
          Mark all read
        </Button>
      </div>

      <Card>
        <CardTitle>Inbox</CardTitle>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-stone-400">Loading…</p>}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <EmptyState
              title="No notifications yet"
              description="Alerts for predictions, reports, invites, and overdue work will show up here."
            />
          )}
          {data?.items.map((n) => (
            <div
              key={n.id}
              className={`flex flex-wrap items-start justify-between gap-3 rounded-xl border px-4 py-3 ${
                n.status === "unread"
                  ? "border-teal-200 bg-teal-50/60 dark:border-teal-900 dark:bg-teal-950/30"
                  : "border-stone-100 dark:border-stone-900"
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{n.title}</p>
                  <StatusBadge status={n.severity} />
                  {n.status === "unread" && (
                    <span className="text-xs text-teal-700 dark:text-teal-300">
                      Unread
                    </span>
                  )}
                </div>
                {n.body && (
                  <p className="mt-1 text-sm text-stone-500">{n.body}</p>
                )}
                <p className="mt-1 text-xs text-stone-400">
                  {n.event_type} · {new Date(n.created_at).toLocaleString()}
                </p>
                {n.link && (
                  <Link
                    href={n.link}
                    className="mt-1 inline-block text-xs text-teal-700 dark:text-teal-300"
                  >
                    Open related
                  </Link>
                )}
              </div>
              {n.status === "unread" && (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={markRead.isPending}
                  onClick={() => markRead.mutate(n.id)}
                >
                  Mark read
                </Button>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
