"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

function VerifyInner() {
  const search = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email…");

  useEffect(() => {
    const token = search.get("token");
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await api.verifyEmail(token);
        if (!cancelled) {
          setStatus("ok");
          setMessage("Email verified. You can continue onboarding.");
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setMessage(err instanceof Error ? err.message : "Verification failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [search]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_rgba(15,118,110,0.12),_transparent_55%)] p-6">
      <Card className="w-full max-w-md">
        <CardTitle>Email verification</CardTitle>
        <CardDescription className="mt-2">{message}</CardDescription>
        {status !== "loading" && (
          <Link
            href={status === "ok" ? "/app/onboarding" : "/login"}
            className="mt-6 inline-flex text-sm font-semibold text-teal-800 hover:underline"
          >
            {status === "ok" ? "Continue to workspace" : "Back to login"}
          </Link>
        )}
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<p className="p-8 text-center text-stone-500">Loading…</p>}>
      <VerifyInner />
    </Suspense>
  );
}
