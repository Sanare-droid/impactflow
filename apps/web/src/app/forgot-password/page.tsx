"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.forgotPassword(email);
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_#ccfbf1_0%,_#fafaf9_45%)] px-4 dark:bg-[radial-gradient(ellipse_at_top,_#134e4a_0%,_#0c0a09_50%)]">
      <Card className="animate-fade-up w-full max-w-md">
        <BrandLogo size={48} priority className="mb-3" />
        <CardTitle className="font-display text-2xl">{APP_NAME}</CardTitle>
        <CardDescription>Request a password reset link.</CardDescription>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {message && <p className="text-sm text-teal-700">{message}</p>}
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Sending…" : "Send reset link"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-stone-500">
          <Link className="text-teal-700 underline dark:text-teal-300" href="/login">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
