"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { useAuth } from "@/providers/auth-provider";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
      return;
    }
    if (
      !loading &&
      user?.must_change_password &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/app/settings")
    ) {
      router.replace("/app/settings?changePassword=1");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-stone-500">
        Loading workspace…
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
