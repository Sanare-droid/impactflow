"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { api, APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.resetPassword({ token, new_password: password });
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="animate-fade-up w-full max-w-md">
      <BrandLogo size={48} priority className="mb-3" />
      <CardTitle className="font-display text-2xl">{APP_NAME}</CardTitle>
      <CardDescription>Choose a new password for your account.</CardDescription>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        {!token && (
          <p className="text-sm text-rose-600">Missing reset token. Use the link from your email.</p>
        )}
        <div>
          <Label htmlFor="password">New password</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="confirm">Confirm password</Label>
          <Input
            id="confirm"
            type="password"
            required
            minLength={12}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <Button className="w-full" disabled={loading || !token} type="submit">
          {loading ? "Saving…" : "Reset password"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-stone-500">
        <Link className="text-teal-700 underline dark:text-teal-300" href="/login">
          Back to sign in
        </Link>
      </p>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_#ccfbf1_0%,_#fafaf9_45%)] px-4 dark:bg-[radial-gradient(ellipse_at_top,_#134e4a_0%,_#0c0a09_50%)]">
      <Suspense fallback={<p className="text-sm text-stone-500">Loading…</p>}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
