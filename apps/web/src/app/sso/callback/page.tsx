"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

function SsoCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const queryError = params.get("error");
    if (queryError) {
      setError(queryError);
      return;
    }

    // SAML ACS redirect places tokens in the URL fragment
    const hash = typeof window !== "undefined" ? window.location.hash.replace(/^#/, "") : "";
    if (hash.includes("access_token=")) {
      const hp = new URLSearchParams(hash);
      const access = hp.get("access_token");
      const refresh = hp.get("refresh_token");
      const orgId = hp.get("organization_id");
      if (access && refresh) {
        void (async () => {
          try {
            api.setSession({
              access_token: access,
              refresh_token: refresh,
              organization_id: orgId || undefined,
            });
            const me = await api.me();
            setUser(me);
            window.history.replaceState(null, "", "/sso/callback");
            router.replace("/app");
          } catch (err) {
            setError(err instanceof Error ? err.message : "SSO login failed");
          }
        })();
        return;
      }
    }

    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Missing OAuth code or state");
      return;
    }
    const redirectUri = `${window.location.origin}/sso/callback`;
    void (async () => {
      try {
        const tokens = await api.ssoCallback({
          code,
          state,
          redirect_uri: redirectUri,
        });
        api.setSession({
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          organization_id:
            tokens.organization_id ?? tokens.user.primary_organization_id,
        });
        setUser(tokens.user);
        router.replace("/app");
      } catch (err) {
        setError(err instanceof Error ? err.message : "SSO login failed");
      }
    })();
  }, [params, router, setUser]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardTitle>Completing SSO…</CardTitle>
        <CardDescription>
          {error ?? "Finishing your organization SSO sign-in."}
        </CardDescription>
      </Card>
    </div>
  );
}

export default function SsoCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-stone-500">Loading…</p>}>
      <SsoCallbackInner />
    </Suspense>
  );
}
