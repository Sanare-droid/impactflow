"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, type SubscriptionPlan } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";

const IMPLEMENTATION_SERVICES = [
  { name: "Onboarding", price: "KES 30,000" },
  { name: "Training", price: "KES 50,000" },
  { name: "Data migration", price: "KES 100,000+" },
  { name: "Custom forms / workflows", price: "Quote" },
  { name: "API integrations", price: "Quote" },
];

const FAQ = [
  {
    q: "How does the free trial work?",
    a: "Register your organization and you automatically receive a 14-day Community trial with surveys, mobile offline capture, and basic dashboards. No credit card required.",
  },
  {
    q: "What are implementation fees?",
    a: "One-time services like onboarding, training, and data migration, billed separately from your subscription. Most useful for larger organizations — contact us for a scoped quote.",
  },
  {
    q: "Can we pay in Kenya Shillings?",
    a: "Yes. Catalog prices are in KES and Paystack checkout charges in KES when configured.",
  },
  {
    q: "What happens when the trial ends?",
    a: "The workspace moves to expired until you upgrade. Billing and exports remain available so you can renew without losing data.",
  },
  {
    q: "How do Government plans work?",
    a: "Government and multilateral contracts are billed manually. Contact sales — a platform admin assigns the Government plan.",
  },
];

const COMPARE_ROWS: { label: string; key: string }[] = [
  { label: "Users", key: "users" },
  { label: "Projects", key: "projects" },
  { label: "Storage", key: "storage" },
  { label: "Survey builder", key: "surveys" },
  { label: "Mobile / offline", key: "mobile" },
  { label: "AI Copilot", key: "ai" },
  { label: "Workflows", key: "workflows" },
  { label: "Marketplace", key: "marketplace" },
  { label: "White label", key: "white_label" },
  { label: "API access", key: "api_access" },
  { label: "Custom domain / SSO", key: "sso" },
];

function formatPrice(plan: SubscriptionPlan, period: "monthly" | "annual") {
  if (plan.contact_sales) return "Contact sales";
  const raw = period === "annual" ? plan.price_annual ?? plan.annual_price : plan.price_monthly ?? plan.monthly_price;
  if (raw == null || Number(raw) <= 0) return "KES 0";
  return `${plan.currency || "KES"} ${Number(raw).toLocaleString()}`;
}

function cellValue(plan: SubscriptionPlan, key: string) {
  const features = new Set([...(plan.features || []), ...(plan.feature_flags || [])]);
  const all = features.has("*");
  switch (key) {
    case "users":
      return plan.seat_limit == null ? "Unlimited" : String(plan.seat_limit);
    case "projects":
      return plan.max_projects == null ? "Unlimited" : String(plan.max_projects);
    case "storage":
      return plan.storage_gb == null ? "Unlimited" : `${plan.storage_gb} GB`;
    case "surveys":
    case "mobile":
      return all || features.has(key) || features.has("offline") ? "✓" : "—";
    case "ai":
    case "workflows":
    case "marketplace":
    case "white_label":
    case "api_access":
      return all || features.has(key) ? "✓" : "—";
    case "sso":
      return all || features.has("sso") || features.has("custom_domains") ? "✓" : "—";
    default:
      return "—";
  }
}

export default function PricingPage() {
  const [period, setPeriod] = useState<"monthly" | "annual">("monthly");
  const plansQ = useQuery({
    queryKey: ["public-billing-plans"],
    queryFn: () => api.listPublicBillingPlans(),
  });

  const plans = useMemo(() => {
    const items = [...(plansQ.data?.items ?? [])];
    items.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    return items;
  }, [plansQ.data]);

  return (
    <div className="min-h-screen bg-[#FFFEFB] text-[#3F3A34]">
      <header className="border-b border-[#E8E2D6]/90 bg-[#FFFEFB]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-2">
            <BrandLogo className="h-8 w-8" />
            <span className="font-display text-lg font-semibold text-[#16324F]">ImpactFlow</span>
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link href="/login" className="text-[#5A534B] hover:text-[#16324F]">
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-md bg-[#1B2A4A] px-3 py-2 font-semibold text-white hover:bg-[#142238]"
            >
              Start free trial
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-[#E8E2D6]/90">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(217,232,184,0.55),_transparent_55%)]" />
          <div className="relative mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5C6B4A]">
              Pricing
            </p>
            <h1 className="font-display mt-3 max-w-3xl text-4xl font-semibold text-[#16324F] md:text-5xl">
              Plans that grow with your programs
            </h1>
            <p className="mt-4 max-w-2xl text-[#5A534B]">
              Start a 14-day free trial. Upgrade with Paystack when you are ready — no manual
              onboarding required.
            </p>

            <div className="mt-8 inline-flex rounded-full border border-[#E8E2D6] bg-white p-1">
              {(["monthly", "annual"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPeriod(p)}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                    period === p
                      ? "bg-[#16324F] text-white"
                      : "text-[#5A534B] hover:text-[#16324F]"
                  }`}
                >
                  {p === "monthly" ? "Monthly" : "Annual (save ~17%)"}
                </button>
              ))}
            </div>

            {plansQ.isLoading && (
              <p className="mt-10 text-sm text-[#7A7268]">Loading plans…</p>
            )}
            {plansQ.isError && (
              <p className="mt-10 text-sm text-rose-700">
                Could not load plans. Check API connectivity.
              </p>
            )}

            <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {plans.map((plan, idx) => {
                const recommended = Boolean(plan.recommended);
                const contact = Boolean(plan.contact_sales);
                return (
                  <article
                    key={plan.id}
                    className={`relative flex flex-col border px-5 py-6 animate-fade-up ${
                      recommended
                        ? "border-[#16324F] bg-[#F7F4EC]"
                        : "border-[#E8E2D6] bg-white"
                    }`}
                    style={{ animationDelay: `${idx * 60}ms` }}
                  >
                    {recommended && (
                      <span className="absolute -top-3 left-5 rounded-full bg-[#2F5D3A] px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
                        ⭐ Most popular
                      </span>
                    )}
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#5C6B4A]">
                      {plan.name}
                    </p>
                    <p className="font-display mt-3 text-3xl font-semibold text-[#16324F]">
                      {formatPrice(plan, period)}
                      {!contact && Number(plan.price_monthly || 0) > 0 && (
                        <span className="text-base font-normal text-[#7A7268]">
                          /{period === "annual" ? "yr" : "mo"}
                        </span>
                      )}
                    </p>
                    <p className="mt-3 flex-1 text-sm leading-relaxed text-[#5A534B]">
                      {plan.description}
                    </p>
                    <ul className="mt-5 space-y-2 text-sm text-[#3F3A34]">
                      <li>
                        {plan.seat_limit == null ? "Unlimited users" : `${plan.seat_limit} users`}
                      </li>
                      <li>
                        {plan.max_projects == null
                          ? "Unlimited projects"
                          : `${plan.max_projects} projects`}
                      </li>
                      <li>
                        {plan.storage_gb == null
                          ? "Unlimited storage"
                          : `${plan.storage_gb} GB storage`}
                      </li>
                      {plan.trial_days > 0 && <li>{plan.trial_days}-day trial</li>}
                    </ul>
                    {contact ? (
                      <a
                        href="mailto:chris@impactflow.space?subject=ImpactFlow%20Government%20plan"
                        className="mt-6 inline-flex justify-center rounded-md border border-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-[#1B2A4A] hover:bg-[#F7F4EC]"
                      >
                        Contact sales
                      </a>
                    ) : plan.code === "enterprise" ? (
                      <div className="mt-6 grid gap-2">
                        <Link
                          href="/register"
                          className="inline-flex justify-center rounded-md bg-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#142238]"
                        >
                          Start free trial
                        </Link>
                        <a
                          href="mailto:chris@impactflow.space?subject=ImpactFlow%20Enterprise"
                          className="inline-flex justify-center rounded-md border border-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-[#1B2A4A]"
                        >
                          Contact sales
                        </a>
                      </div>
                    ) : (
                      <Link
                        href="/register"
                        className={`mt-6 inline-flex justify-center rounded-md px-4 py-2.5 text-sm font-semibold ${
                          recommended
                            ? "bg-[#1B2A4A] text-white hover:bg-[#142238]"
                            : "border border-[#1B2A4A] text-[#1B2A4A] hover:bg-[#F7F4EC]"
                        }`}
                      >
                        {plan.code === "free" ? "Start free trial" : "Upgrade after trial"}
                      </Link>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 md:px-8">
          <h2 className="font-display text-3xl font-semibold text-[#16324F]">Compare features</h2>
          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[#E8E2D6] text-left">
                  <th className="py-3 pr-4 font-semibold text-[#16324F]">Capability</th>
                  {plans.map((p) => (
                    <th key={p.id} className="px-3 py-3 font-semibold text-[#16324F]">
                      {p.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARE_ROWS.map((row) => (
                  <tr key={row.key} className="border-b border-[#F0EBE3]">
                    <td className="py-3 pr-4 text-[#5A534B]">{row.label}</td>
                    {plans.map((p) => (
                      <td key={p.id} className="px-3 py-3 text-[#3F3A34]">
                        {cellValue(p, row.key)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 md:px-8">
          <h2 className="font-display text-3xl font-semibold text-[#16324F]">
            Implementation services
          </h2>
          <p className="mt-3 max-w-2xl text-[#5A534B]">
            One-time services to get your organization live faster. Billed separately from your
            subscription — especially valuable for larger organizations and government programs.
          </p>
          <div className="mt-8 max-w-2xl overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[#E8E2D6] text-left">
                  <th className="py-3 pr-4 font-semibold text-[#16324F]">Service</th>
                  <th className="py-3 font-semibold text-[#16324F]">Price (one-time)</th>
                </tr>
              </thead>
              <tbody>
                {IMPLEMENTATION_SERVICES.map((s) => (
                  <tr key={s.name} className="border-b border-[#F0EBE3]">
                    <td className="py-3 pr-4 text-[#5A534B]">{s.name}</td>
                    <td className="py-3 text-[#3F3A34]">{s.price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <a
            href="mailto:chris@impactflow.space?subject=ImpactFlow%20implementation%20services"
            className="mt-6 inline-flex rounded-md border border-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-[#1B2A4A] hover:bg-[#F7F4EC]"
          >
            Request a quote
          </a>
        </section>

        <section className="border-y border-[#E8E2D6]/90 bg-[#F7F4EC]/60">
          <div className="mx-auto max-w-6xl px-5 py-16 md:px-8">
            <h2 className="font-display text-3xl font-semibold text-[#16324F]">Built for East Africa</h2>
            <p className="mt-3 text-[#5A534B]">
              Designed for NGOs, foundations, and public-sector partners running field programs across
              the region.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
              {["Horizon Trust", "Lake Basin Alliance", "Civic Metrics", "Sahel Partners"].map(
                (name) => (
                  <div
                    key={name}
                    className="flex h-20 items-center justify-center border border-[#D9D2C5] bg-white/70 text-sm font-medium text-[#7A7268]"
                  >
                    {name}
                  </div>
                ),
              )}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 md:px-8">
          <h2 className="font-display text-3xl font-semibold text-[#16324F]">Security</h2>
          <p className="mt-3 max-w-2xl text-[#5A534B]">
            Multi-tenant isolation, audit logs, role-based access, and Paystack-secured checkout.
            Payments are verified server-side — never trust a browser redirect alone.
          </p>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-20 md:px-8">
          <h2 className="font-display text-3xl font-semibold text-[#16324F]">FAQ</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            {FAQ.map((item) => (
              <div key={item.q}>
                <h3 className="font-semibold text-[#16324F]">{item.q}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[#5A534B]">{item.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
