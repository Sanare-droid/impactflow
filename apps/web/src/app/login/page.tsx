"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, APP_NAME } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { useAuth } from "@/providers/auth-provider";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokens = await api.login({
        email,
        password,
        organization_slug: organizationSlug || undefined,
        mfa_code: mfaCode || undefined,
      });
      if (tokens.mfa_required) {
        setMfaRequired(true);
        return;
      }
      api.setSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        organization_id: tokens.user.primary_organization_id,
      });
      setUser(tokens.user);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_#ccfbf1_0%,_#fafaf9_45%)] px-4 dark:bg-[radial-gradient(ellipse_at_top,_#134e4a_0%,_#0c0a09_50%)]">
      <Card className="animate-fade-up w-full max-w-md">
        <CardTitle className="font-display text-2xl">{APP_NAME}</CardTitle>
        <CardDescription>Sign in to your organization workspace.</CardDescription>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="slug">Organization slug (optional)</Label>
            <Input
              id="slug"
              value={organizationSlug}
              onChange={(e) => setOrganizationSlug(e.target.value)}
              placeholder="hope-foundation"
            />
          </div>
          {mfaRequired && (
            <div>
              <Label htmlFor="mfa">Authenticator code</Label>
              <Input
                id="mfa"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder="123456"
                required
              />
            </div>
          )}
          {error && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              {error}
            </p>
          )}
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-stone-500">
          New organization?{" "}
          <Link className="text-teal-700 underline dark:text-teal-300" href="/register">
            Create workspace
          </Link>
        </p>
      </Card>
    </div>
  );
}
