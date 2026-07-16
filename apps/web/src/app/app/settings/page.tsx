"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { useAuth } from "@/providers/auth-provider";

function SettingsContent() {
  const { user, refreshMe } = useAuth();
  const searchParams = useSearchParams();
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [mfaUri, setMfaUri] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forceChange, setForceChange] = useState(false);

  useEffect(() => {
    if (searchParams.get("changePassword") === "1" || user?.must_change_password) {
      setForceChange(true);
    }
  }, [searchParams, user?.must_change_password]);

  async function setupMfa() {
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/auth/mfa/setup`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("if_access_token")}`,
          },
        },
      );
      if (!res.ok) throw new Error("Unable to start MFA setup");
      const data = await res.json();
      setMfaSecret(data.secret);
      setMfaUri(data.provisioning_uri);
    } catch (err) {
      setError(err instanceof Error ? err.message : "MFA setup failed");
    }
  }

  async function enableMfa() {
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/auth/mfa/enable`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("if_access_token")}`,
          },
          body: JSON.stringify({ code }),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message || body.detail?.message || "Unable to enable MFA");
      }
      setMessage("MFA enabled successfully");
      setMfaSecret(null);
      setMfaUri(null);
      setCode("");
      await refreshMe();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enable failed");
    }
  }

  async function onChangePassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage("Password updated");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setForceChange(false);
      await refreshMe();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed");
    }
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-stone-500">Security and personal preferences.</p>
      </div>

      {forceChange && (
        <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30">
          <CardTitle>Password change required</CardTitle>
          <CardDescription>
            Your account uses a temporary password. Set a new password to continue.
          </CardDescription>
        </Card>
      )}

      <Card>
        <CardTitle>Change password</CardTitle>
        <CardDescription>Use at least 12 characters with upper, lower, and a digit.</CardDescription>
        <form className="mt-4 grid max-w-md gap-3" onSubmit={onChangePassword}>
          <div>
            <Label htmlFor="current">Current password</Label>
            <Input
              id="current"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="new">New password</Label>
            <Input
              id="new"
              type="password"
              required
              minLength={12}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="confirm">Confirm new password</Label>
            <Input
              id="confirm"
              type="password"
              required
              minLength={12}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <Button type="submit">Update password</Button>
        </form>
      </Card>

      <Card>
        <CardTitle>Multi-factor authentication</CardTitle>
        <CardDescription>
          Protect administrator and sensitive accounts with TOTP-based MFA.
        </CardDescription>
        <p className="mt-4 text-sm text-stone-600 dark:text-stone-300">
          Status:{" "}
          <span className="font-medium">
            {user?.mfa_enabled ? "Enabled" : "Not enabled"}
          </span>
        </p>
        {!user?.mfa_enabled && (
          <div className="mt-4 space-y-4">
            <Button onClick={setupMfa} variant="secondary">
              Start MFA setup
            </Button>
            {mfaSecret && (
              <div className="rounded-xl bg-stone-50 p-4 text-sm dark:bg-stone-900">
                <p className="font-medium">Secret</p>
                <p className="mt-1 break-all font-mono text-xs">{mfaSecret}</p>
                {mfaUri && (
                  <p className="mt-3 break-all text-xs text-stone-500">{mfaUri}</p>
                )}
                <div className="mt-4 max-w-xs">
                  <Label htmlFor="code">Verification code</Label>
                  <Input
                    id="code"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="123456"
                  />
                  <Button className="mt-3" onClick={enableMfa}>
                    Enable MFA
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card>
        <CardTitle>Session</CardTitle>
        <CardDescription>
          Access tokens expire quickly; refresh tokens rotate on each use.
        </CardDescription>
        <p className="mt-4 text-sm text-stone-500">
          Signed in as {user?.email}. API base:{" "}
          {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
        </p>
      </Card>

      {message && <p className="text-sm text-teal-700">{message}</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-stone-500">Loading settings…</p>}>
      <SettingsContent />
    </Suspense>
  );
}
