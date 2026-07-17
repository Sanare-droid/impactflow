"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

const selectClassName =
  "mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-950";

export default function UsersPage() {
  const qc = useQueryClient();
  const { user: currentUser } = useAuth();
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [roleId, setRoleId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);
  const [emailDeliveryStatus, setEmailDeliveryStatus] = useState<string | null>(null);

  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers({ page_size: 100 }),
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.roles(),
  });

  const { data: usage } = useQuery({
    queryKey: ["billing-usage"],
    queryFn: () => api.getBillingUsage(),
    retry: false,
  });

  const defaultRoleId = useMemo(() => {
    if (!roles?.length) return "";
    const field = roles.find((r) => r.slug === "field_officer");
    return field?.id ?? roles[0]?.id ?? "";
  }, [roles]);

  useEffect(() => {
    if (!roleId && defaultRoleId) setRoleId(defaultRoleId);
  }, [defaultRoleId, roleId]);

  const invite = useMutation({
    mutationFn: () =>
      api.inviteUser({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        role_id: roleId,
        job_title: jobTitle.trim() || null,
        send_invite: true,
      }),
    onSuccess: async (res) => {
      setError(null);
      setEmail("");
      setFirstName("");
      setLastName("");
      setJobTitle("");
      setRoleId(defaultRoleId);
      setInviteMessage(res.message);
      setEmailDeliveryStatus(res.email_delivery?.status ?? null);
      setTempPassword(res.temporary_password ?? null);
      await qc.invalidateQueries({ queryKey: ["users"] });
      await qc.invalidateQueries({ queryKey: ["billing-usage"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => {
      setTempPassword(null);
      setInviteMessage(null);
      setEmailDeliveryStatus(null);
      setError(err.message);
    },
  });

  const changeRole = useMutation({
    mutationFn: ({ membershipId, nextRoleId }: { membershipId: string; nextRoleId: string }) =>
      api.updateMembershipRole(membershipId, nextRoleId),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const seatsUsed = usage?.users.used;
  const seatsLimit = usage?.users.limit;
  const seatsLabel =
    seatsUsed != null
      ? seatsLimit != null
        ? `${seatsUsed} / ${seatsLimit} seats used`
        : `${seatsUsed} seats used (unlimited plan)`
      : null;

  function onInvite(e: FormEvent) {
    e.preventDefault();
    if (!roleId) {
      setError("Select a role for the invite.");
      return;
    }
    invite.mutate();
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Users</h1>
        <p className="mt-2 text-stone-500">
          Invite teammates, assign roles, and manage who can use web and the field app.
          {seatsLabel ? ` ${seatsLabel}.` : ""}
        </p>
      </div>

      {(error || loadError) && (
        <p className="text-sm text-rose-600">
          {error || (loadError as Error).message}
          {error?.toLowerCase().includes("seat") || error?.toLowerCase().includes("user") ? (
            <>
              {" "}
              <Link href="/app/billing" className="underline">
                Upgrade plan
              </Link>
            </>
          ) : null}
        </p>
      )}

      {inviteMessage && (
        <Card
          className={
            emailDeliveryStatus === "not_configured" ||
            emailDeliveryStatus === "failed" ||
            emailDeliveryStatus === "queued_stub" ||
            inviteMessage.includes("Resend's test domain")
              ? "border-amber-200 bg-amber-50/60 dark:border-amber-900 dark:bg-amber-950/30"
              : "border-teal-200 bg-teal-50/50 dark:border-teal-900 dark:bg-teal-950/30"
          }
        >
          <CardTitle>
            {emailDeliveryStatus === "not_configured" || emailDeliveryStatus === "queued_stub"
              ? "Invite created — share password manually"
              : emailDeliveryStatus === "failed" ||
                  inviteMessage.includes("Resend's test domain")
                ? "Invite created — check email setup"
                : "Invite created"}
          </CardTitle>
          <CardDescription>{inviteMessage}</CardDescription>
          {tempPassword && (
            <div className="mt-3 rounded-lg bg-white/80 px-3 py-2 text-sm dark:bg-stone-950/60">
              <p className="font-medium text-stone-800 dark:text-stone-100">
                Temporary password (copy now — shown once)
              </p>
              <code className="mt-1 block break-all text-teal-800 dark:text-teal-200">
                {tempPassword}
              </code>
              <button
                type="button"
                className="mt-2 text-xs font-medium text-teal-800 underline dark:text-teal-200"
                onClick={() => void navigator.clipboard.writeText(tempPassword)}
              >
                Copy password
              </button>
            </div>
          )}
        </Card>
      )}

      <Card>
        <CardTitle>Invite teammate</CardTitle>
        <CardDescription>
          Field Officers get mobile sync. Managers and MEAL officers are web-focused. Each active
          member uses one billing seat.
        </CardDescription>
        <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onInvite}>
          <div>
            <Label htmlFor="invite-email">Work email</Label>
            <Input
              id="invite-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@organization.org"
            />
          </div>
          <div>
            <Label htmlFor="invite-role">Role</Label>
            <select
              id="invite-role"
              className={selectClassName}
              required
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
            >
              <option value="" disabled>
                Select role
              </option>
              {(roles ?? []).map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                  {role.slug === "field_officer" ? " (mobile field)" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="invite-first">First name</Label>
            <Input
              id="invite-first"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="invite-last">Last name</Label>
            <Input
              id="invite-last"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="invite-job">Job title (optional)</Label>
            <Input
              id="invite-job"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="Field officer — County A"
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={invite.isPending || !roleId}>
              {invite.isPending ? "Inviting…" : "Send invite"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Members</CardTitle>
        <CardDescription>
          All memberships are tenant-scoped and audited. Change roles anytime — Field Officer is
          required for offline sync on mobile.
        </CardDescription>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Email</th>
                <th className="pb-3 font-medium">Role</th>
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
              {data?.items.map((item) => {
                const isSelf = currentUser?.id === item.user_id;
                return (
                  <tr
                    key={item.id}
                    className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                  >
                    <td className="py-3 font-medium">
                      {item.user
                        ? `${item.user.first_name} ${item.user.last_name}`
                        : "—"}
                      {isSelf ? (
                        <span className="ml-2 text-xs font-normal text-stone-400">(you)</span>
                      ) : null}
                    </td>
                    <td className="py-3 text-stone-600 dark:text-stone-300">
                      {item.user?.email ?? "—"}
                    </td>
                    <td className="py-3">
                      <select
                        className="w-full max-w-[220px] rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-sm dark:border-stone-700 dark:bg-stone-950"
                        value={item.role_id}
                        disabled={changeRole.isPending || isSelf}
                        title={
                          isSelf
                            ? "Ask another admin to change your role"
                            : "Change member role"
                        }
                        onChange={(e) => {
                          const next = e.target.value;
                          if (next === item.role_id) return;
                          changeRole.mutate({ membershipId: item.id, nextRoleId: next });
                        }}
                      >
                        {(roles ?? []).map((role) => (
                          <option key={role.id} value={role.id}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3">
                      <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-200">
                        {item.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
