"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { useAuth } from "@/providers/auth-provider";
import { ORGANIZATION_TYPES } from "@/lib/organization-types";

export default function RegisterPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [form, setForm] = useState({
    organization_name: "",
    organization_slug: "",
    organization_type: "ngo",
    country_code: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokens = await api.register({
        ...form,
        country_code: form.country_code || null,
        organization_slug: form.organization_slug || null,
      });
      api.setSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        organization_id: tokens.user.primary_organization_id,
      });
      setUser(tokens.user);
      router.push("/app/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_#0f766e33_0%,_#fafaf9_42%)] px-4 py-10 dark:bg-[radial-gradient(ellipse_at_top,_#134e4a_0%,_#0c0a09_45%)]">
      <Card className="animate-fade-up w-full max-w-xl">
        <BrandLogo size={48} priority className="mb-3" />
        <CardTitle className="font-display text-2xl">
          Create your {APP_NAME} workspace
        </CardTitle>
        <CardDescription>
          Register your organization and become the first admin.
        </CardDescription>
        <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
          <div className="md:col-span-2">
            <Label htmlFor="org">Organization name</Label>
            <Input
              id="org"
              required
              value={form.organization_name}
              onChange={(e) => update("organization_name", e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="slug">Slug</Label>
            <Input
              id="slug"
              value={form.organization_slug}
              onChange={(e) => update("organization_slug", e.target.value)}
              placeholder="auto-generated if empty"
            />
          </div>
          <div>
            <Label htmlFor="type">Organization type</Label>
            <select
              id="type"
              required
              value={form.organization_type}
              onChange={(e) => update("organization_type", e.target.value)}
              className="flex h-10 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/30 dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100"
            >
              {ORGANIZATION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="first">First name</Label>
            <Input
              id="first"
              required
              value={form.first_name}
              onChange={(e) => update("first_name", e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="last">Last name</Label>
            <Input
              id="last"
              required
              value={form.last_name}
              onChange={(e) => update("last_name", e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="password">Password (8+ chars, mixed case, digit)</Label>
            <Input
              id="password"
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="country">Country code</Label>
            <Input
              id="country"
              maxLength={2}
              value={form.country_code}
              onChange={(e) => update("country_code", e.target.value.toUpperCase())}
              placeholder="KE"
            />
          </div>
          {error && (
            <div className="md:col-span-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              <p>{error}</p>
            </div>
          )}
          <div className="md:col-span-2">
            <Button className="w-full" disabled={loading} type="submit">
              {loading ? "Creating workspace…" : "Create workspace"}
            </Button>
          </div>
        </form>
        <p className="mt-4 text-sm text-stone-500">
          Already have access?{" "}
          <Link className="text-teal-700 underline dark:text-teal-300" href="/login">
            Sign in
          </Link>
        </p>
        <p className="mt-3 text-xs text-stone-400">
          By creating a workspace you agree to our{" "}
          <Link className="underline hover:text-stone-600" href="/terms">
            Terms
          </Link>{" "}
          and{" "}
          <Link className="underline hover:text-stone-600" href="/privacy">
            Privacy Policy
          </Link>
          .
        </p>
      </Card>
    </div>
  );
}
