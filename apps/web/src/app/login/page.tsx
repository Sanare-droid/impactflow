"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, APP_NAME, type PublicBranding } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
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
  const [branding, setBranding] = useState<PublicBranding | null>(null);

  useEffect(() => {
    const slug = organizationSlug.trim().toLowerCase();
    if (slug.length < 2) {
      setBranding(null);
      return;
    }
    const handle = setTimeout(() => {
      void api
        .getPublicBranding(slug)
        .then((b) => setBranding(b.is_enabled ? b : null))
        .catch(() => setBranding(null));
    }, 350);
    return () => clearTimeout(handle);
  }, [organizationSlug]);

  const productName = branding?.product_name || APP_NAME;
  const tagline =
    branding?.tagline || "Sign in to your organization workspace.";
  const primary = branding?.primary_color || "#0F766E";

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
      if (tokens.user.must_change_password) {
        router.push("/app/settings?changePassword=1");
      } else {
        router.push("/app");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{
        background: branding?.login_background_url
          ? `linear-gradient(rgba(15,23,42,0.45), rgba(15,23,42,0.55)), url(${branding.login_background_url}) center/cover`
          : `radial-gradient(ellipse at top, ${primary}33 0%, #fafaf9 45%)`,
      }}
    >
      <Card className="animate-fade-up w-full max-w-md">
        {branding?.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={branding.logo_url}
            alt={productName}
            className="mb-3 h-12 w-auto object-contain"
          />
        ) : (
          <BrandLogo size={56} priority className="mb-3" />
        )}
        <CardTitle className="font-display text-2xl" style={{ color: primary }}>
          {productName}
        </CardTitle>
        <CardDescription>{tagline}</CardDescription>
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
          <Button
            className="w-full"
            disabled={loading}
            type="submit"
            style={{ backgroundColor: primary }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-stone-500">
          <Link className="text-teal-700 underline dark:text-teal-300" href="/forgot-password">
            Forgot password?
          </Link>
        </p>
        <p className="mt-2 text-sm text-stone-500">
          New organization?{" "}
          <Link className="text-teal-700 underline dark:text-teal-300" href="/register">
            Create workspace
          </Link>
        </p>
        {branding && !branding.hide_powered_by ? (
          <p className="mt-4 text-center text-xs text-stone-400">Powered by ImpactFlow AI</p>
        ) : null}
      </Card>
    </div>
  );
}
