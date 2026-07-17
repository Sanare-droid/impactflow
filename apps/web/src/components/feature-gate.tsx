"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Props = {
  feature: string;
  children: React.ReactNode;
  fallbackTitle?: string;
};

export function FeatureGate({
  feature,
  children,
  fallbackTitle = "Upgrade to unlock",
}: Props) {
  const features = useQuery({ queryKey: ["features"], queryFn: () => api.getFeatures() });
  const enabled = features.data?.features?.[feature];

  if (features.isLoading) {
    return <p className="text-sm text-stone-500">Checking plan access…</p>;
  }

  if (enabled) return <>{children}</>;

  return (
    <div className="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-8 text-center">
      <h2 className="font-display text-xl font-semibold text-stone-900">{fallbackTitle}</h2>
      <p className="mt-2 text-sm text-stone-600">
        <code className="rounded bg-stone-100 px-1.5 py-0.5 text-xs">{feature}</code> is not
        included in your current plan.
      </p>
      <Link href="/app/billing" className="mt-5 inline-block">
        <Button>View billing & upgrade</Button>
      </Link>
    </div>
  );
}
