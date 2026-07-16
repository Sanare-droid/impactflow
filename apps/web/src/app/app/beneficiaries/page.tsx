"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";

export default function BeneficiariesPage() {
  const qc = useQueryClient();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [sex, setSex] = useState("female");
  const [phone, setPhone] = useState("");
  const [householdId, setHouseholdId] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [consent, setConsent] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { data: households } = useQuery({
    queryKey: ["households"],
    queryFn: () => api.listHouseholds(),
  });
  const { data: communities } = useQuery({
    queryKey: ["communities"],
    queryFn: () => api.listCommunities(),
  });
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(),
  });
  const { data, isLoading } = useQuery({
    queryKey: ["beneficiaries"],
    queryFn: () => api.listBeneficiaries(),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createBeneficiary({
        first_name: firstName,
        last_name: lastName,
        sex,
        phone: phone || undefined,
        household_id: householdId || undefined,
        community_id: communityId || undefined,
        consent_data_use: consent,
        status: "active",
        memberships: projectId
          ? [{ project_id: projectId, status: "enrolled", membership_role: "participant" }]
          : undefined,
      }),
    onSuccess: async () => {
      setFirstName("");
      setLastName("");
      setPhone("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["beneficiaries"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Beneficiaries</h1>
        <p className="mt-2 text-stone-500">
          Individual registration, household linkage, and program membership.
        </p>
      </div>

      <Card>
        <CardTitle>Register beneficiary</CardTitle>
        <CardDescription>
          Field-ready registration with optional project enrollment.
        </CardDescription>
        <form
          className="mt-4 grid gap-3 md:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label htmlFor="first">First name</Label>
            <Input
              id="first"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="last">Last name</Label>
            <Input
              id="last"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="sex">Sex</Label>
            <select
              id="sex"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={sex}
              onChange={(e) => setSex(e.target.value)}
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="community">Community</Label>
            <select
              id="community"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={communityId}
              onChange={(e) => setCommunityId(e.target.value)}
            >
              <option value="">None</option>
              {communities?.items.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="hh">Household</Label>
            <select
              id="hh"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={householdId}
              onChange={(e) => setHouseholdId(e.target.value)}
            >
              <option value="">None</option>
              {households?.items.map((hh) => (
                <option key={hh.id} value={hh.id}>
                  {hh.name}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="project">Enroll in project (optional)</Label>
            <select
              id="project"
              className="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-950"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              <option value="">None</option>
              {projects?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <label className="md:col-span-2 flex items-center gap-2 text-sm text-stone-600 dark:text-stone-300">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            Consent for data use recorded
          </label>
          {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
          <div className="md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Register beneficiary"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardTitle>Beneficiary caseload</CardTitle>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-stone-200 text-stone-500 dark:border-stone-800">
              <tr>
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Code</th>
                <th className="pb-3 font-medium">Sex</th>
                <th className="pb-3 font-medium">Phone</th>
                <th className="pb-3 font-medium">Memberships</th>
                <th className="pb-3 font-medium">Status</th>
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
              {data?.items.map((b) => (
                <tr
                  key={b.id}
                  className="border-b border-stone-100 last:border-0 dark:border-stone-900"
                >
                  <td className="py-3 font-medium">
                    {b.first_name} {b.last_name}
                    {b.is_household_head ? (
                      <span className="ml-2 text-xs text-stone-400">head</span>
                    ) : null}
                  </td>
                  <td className="py-3 font-mono text-xs">{b.code}</td>
                  <td className="py-3 capitalize">{b.sex || "—"}</td>
                  <td className="py-3">{b.phone || "—"}</td>
                  <td className="py-3">{b.memberships?.length ?? 0}</td>
                  <td className="py-3">
                    <StatusBadge status={b.status} />
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
