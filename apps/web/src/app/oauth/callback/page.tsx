"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

/**
 * Connector OAuth return URL. Completes token exchange against the hub API
 * when the user is already signed into ImpactFlow.
 */
function OAuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [message, setMessage] = useState("Completing connector OAuth…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Missing OAuth code or state from the provider.");
      return;
    }
    const redirectUri = `${window.location.origin}/oauth/callback`;
    void (async () => {
      try {
        await api.oauthCallback({ code, state, redirect_uri: redirectUri });
        setMessage("Connector connected. You can return to Integrations.");
      } catch (err) {
        setError(err instanceof Error ? err.message : "OAuth callback failed");
      }
    })();
  }, [params]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md space-y-4">
        <CardTitle>Integrations OAuth</CardTitle>
        <CardDescription>{error ?? message}</CardDescription>
        <Button onClick={() => router.push("/app/integrations")}>
          Back to Integrations
        </Button>
        <Link href="/app" className="block text-sm text-teal-700 underline">
          Dashboard
        </Link>
      </Card>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-stone-500">Loading…</p>}>
      <OAuthCallbackInner />
    </Suspense>
  );
}
