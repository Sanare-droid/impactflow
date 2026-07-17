import type { Metadata } from "next";
import Link from "next/link";
import { BrandLogo } from "@/components/brand-logo";

const siteUrl =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  "https://impactflow.africa";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "Terms governing use of the ImpactFlow enterprise SaaS platform operated by StemCloud Technologies.",
  alternates: { canonical: `${siteUrl}/terms` },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Terms of Service · ImpactFlow",
    description:
      "Terms governing use of the ImpactFlow enterprise SaaS platform.",
    url: `${siteUrl}/terms`,
  },
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#FFFEFB] text-[#3F3A34] dark:bg-stone-950 dark:text-stone-200">
      <header className="border-b border-[#E8E2D6]/90 bg-[#FFFEFB]/90 backdrop-blur dark:border-stone-800 dark:bg-stone-950/90">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-2">
            <BrandLogo size={32} />
            <span className="font-display text-lg font-semibold text-[#16324F] dark:text-stone-100">
              ImpactFlow
            </span>
          </Link>
          <Link href="/privacy" className="text-sm text-[#5A534B] hover:text-[#16324F]">
            Privacy Policy
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-14 md:px-8 md:py-20">
        <span className="rounded-full border border-[#D9E8B8] bg-[#F4F7EF] px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[#2F5D3A]">
          Last updated · 17 July 2026
        </span>
        <h1 className="font-display mt-5 text-4xl font-semibold text-[#16324F] dark:text-stone-50">
          Terms of Service
        </h1>
        <p className="mt-4 text-[#5A534B] dark:text-stone-400">
          These Terms govern access to ImpactFlow, an enterprise SaaS platform operated by
          StemCloud Technologies (“we”, “us”). By registering or using the service you agree
          to these Terms on behalf of yourself or your organization.
        </p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed text-[#4A453E] dark:text-stone-300">
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              1. The service
            </h2>
            <p className="mt-2">
              ImpactFlow provides multi-tenant software for program management, MEAL, field
              operations, surveys, reporting, workflows, and related mobile offline capture.
              Features depend on your subscription plan.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              2. Accounts and organizations
            </h2>
            <p className="mt-2">
              You must provide accurate registration information and keep credentials
              confidential. Organization administrators control roles, invites, and data
              within their tenant. You are responsible for activity under your accounts.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              3. Customer data
            </h2>
            <p className="mt-2">
              Your organization retains ownership of program and field data uploaded to its
              workspace. You grant us a limited license to host, process, and display that
              data solely to provide the service. Our handling of personal data is described
              in the{" "}
              <Link href="/privacy" className="font-medium text-[#0F766E] underline-offset-2 hover:underline">
                Privacy Policy
              </Link>
              .
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              4. Acceptable use
            </h2>
            <p className="mt-2">
              You may not misuse the platform, attempt unauthorized access, disrupt other
              tenants, violate law, or process data without a lawful basis. We may suspend
              access for material breaches or security risk.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              5. Subscriptions and billing
            </h2>
            <p className="mt-2">
              Paid plans are billed according to the selected catalog (KES) and payment
              provider terms (for example Paystack). Trials convert according to the
              published plan rules. Fees are non-refundable except where required by law or
              written agreement.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              6. AI features
            </h2>
            <p className="mt-2">
              Optional AI features generate suggestions that must be reviewed by humans.
              AI outputs may be inaccurate; you remain responsible for decisions and
              published content.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              7. Disclaimers and liability
            </h2>
            <p className="mt-2">
              The service is provided “as is” to the extent permitted by law. Our aggregate
              liability for claims relating to the service is limited to fees paid for the
              three months preceding the claim, except for liability that cannot be limited
              by law.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-[#16324F] dark:text-stone-100">
              8. Contact
            </h2>
            <p className="mt-2">
              StemCloud Technologies ·{" "}
              <a href="mailto:support@impactflow.africa" className="text-[#0F766E] hover:underline">
                support@impactflow.africa
              </a>
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
