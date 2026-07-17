"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BrandLogo } from "@/components/brand-logo";

const LAST_UPDATED = "17 July 2026";
const COMPANY = "StemCloud Technologies";

const SECTIONS = [
  { id: "introduction", label: "1. Introduction" },
  { id: "information-we-collect", label: "2. Information We Collect" },
  { id: "how-information-is-used", label: "3. How Information Is Used" },
  { id: "ai-services", label: "4. AI Services" },
  { id: "offline-data", label: "5. Offline Data Collection" },
  { id: "cookies", label: "6. Cookies" },
  { id: "how-data-is-shared", label: "7. How Data Is Shared" },
  { id: "third-party-services", label: "8. Third-Party Services" },
  { id: "security", label: "9. Security" },
  { id: "data-retention", label: "10. Data Retention" },
  { id: "user-rights", label: "11. User Rights" },
  { id: "international-transfers", label: "12. International Transfers" },
  { id: "children", label: "13. Children" },
  { id: "government", label: "14. Government Organizations" },
  { id: "data-protection", label: "15. Data Protection" },
  { id: "policy-updates", label: "16. Policy Updates" },
  { id: "contact", label: "17. Contact" },
] as const;

function SectionCard({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="scroll-mt-28 rounded-2xl border border-[#E8E2D6] bg-white p-6 shadow-[0_1px_0_rgba(22,50,79,0.04)] animate-fade-up md:p-8 dark:border-stone-800 dark:bg-stone-950/60"
    >
      <h2 className="font-display text-2xl font-semibold tracking-tight text-[#16324F] dark:text-stone-100">
        {title}
      </h2>
      <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-[#4A453E] dark:text-stone-300">
        {children}
      </div>
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#2F5D3A]" aria-hidden />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function PrivacyPolicyView() {
  const [active, setActive] = useState<string>(SECTIONS[0].id);

  useEffect(() => {
    const nodes = SECTIONS.map((s) => document.getElementById(s.id)).filter(
      Boolean,
    ) as HTMLElement[];
    if (!nodes.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: "-20% 0px -55% 0px", threshold: [0.1, 0.35, 0.6] },
    );

    nodes.forEach((n) => observer.observe(n));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-[#FFFEFB] text-[#3F3A34] dark:bg-stone-950 dark:text-stone-200">
      <header className="no-print sticky top-0 z-40 border-b border-[#E8E2D6]/90 bg-[#FFFEFB]/90 backdrop-blur dark:border-stone-800 dark:bg-stone-950/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-2">
            <BrandLogo size={32} />
            <span className="font-display text-lg font-semibold text-[#16324F] dark:text-stone-100">
              ImpactFlow
            </span>
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link href="/pricing" className="hidden text-[#5A534B] hover:text-[#16324F] sm:inline dark:text-stone-400">
              Pricing
            </Link>
            <Link href="/login" className="text-[#5A534B] hover:text-[#16324F] dark:text-stone-400">
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

      <div className="relative overflow-hidden border-b border-[#E8E2D6]/90 dark:border-stone-800">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(217,232,184,0.55),_transparent_55%)] dark:bg-[radial-gradient(ellipse_at_top,_rgba(47,93,58,0.25),_transparent_55%)]" />
        <div className="relative mx-auto max-w-6xl px-5 py-14 md:px-8 md:py-20">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-[#D9E8B8] bg-[#F4F7EF] px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[#2F5D3A] dark:border-stone-700 dark:bg-stone-900 dark:text-teal-300">
              Last updated · {LAST_UPDATED}
            </span>
            <span className="rounded-full border border-[#E8E2D6] bg-white px-3 py-1 text-xs font-medium text-[#5A534B] dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300">
              {COMPANY}
            </span>
          </div>
          <h1 className="font-display mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-[#16324F] md:text-5xl dark:text-stone-50">
            Privacy Policy
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-[#5A534B] md:text-lg dark:text-stone-400">
            How ImpactFlow collects, uses, stores and protects information across our web
            platform and mobile applications.
          </p>
          <p className="mt-3 max-w-2xl text-sm text-[#7A7268] dark:text-stone-500">
            This policy applies to ImpactFlow Field (Android / iOS), the ImpactFlow web
            console, APIs, and related enterprise SaaS services operated by {COMPANY}.
          </p>
        </div>
      </div>

      <main className="mx-auto grid max-w-6xl gap-10 px-5 py-12 md:px-8 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-12 lg:py-16">
        <aside className="no-print lg:sticky lg:top-28 lg:self-start">
          <nav
            aria-label="Privacy policy table of contents"
            className="rounded-2xl border border-[#E8E2D6] bg-white/90 p-4 dark:border-stone-800 dark:bg-stone-950/70"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#5C6B4A] dark:text-stone-500">
              On this page
            </p>
            <ol className="mt-3 max-h-[70vh] space-y-1 overflow-y-auto text-sm">
              {SECTIONS.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    className={`block rounded-lg px-2.5 py-1.5 transition ${
                      active === section.id
                        ? "bg-[#F7F4EC] font-medium text-[#16324F] dark:bg-stone-900 dark:text-teal-200"
                        : "text-[#5A534B] hover:bg-[#F7F4EC]/70 hover:text-[#16324F] dark:text-stone-400 dark:hover:bg-stone-900"
                    }`}
                  >
                    {section.label}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        </aside>

        <article className="privacy-print space-y-6" itemScope itemType="https://schema.org/PrivacyPolicy">
          <SectionCard id="introduction" title="1. Introduction">
            <p>
              ImpactFlow is an enterprise software-as-a-service (SaaS) platform built for
              organizations that deliver development, humanitarian, conservation, and
              research programs. Typical customers include:
            </p>
            <BulletList
              items={[
                "Non-governmental organizations (NGOs)",
                "Governments and public agencies",
                "Conservation organizations",
                "Foundations and philanthropic partners",
                "Development partners and implementing agencies",
                "Humanitarian organizations",
                "Research institutions",
              ]}
            />
            <p>The platform enables teams to plan and deliver work across:</p>
            <BulletList
              items={[
                "Project and program management",
                "Monitoring and evaluation (MEAL)",
                "Field operations",
                "Surveys and forms",
                "Reporting and dashboards",
                "AI-assisted analysis",
                "Workflow automation",
                "Offline mobile data collection",
              ]}
            />
            <p>
              By creating an account, installing ImpactFlow Field, or using our services,
              you acknowledge this Privacy Policy. Organization administrators remain
              responsible for how their workspace configures collection of beneficiary and
              field data under applicable law and donor requirements.
            </p>
          </SectionCard>

          <SectionCard id="information-we-collect" title="2. Information We Collect">
            <h3 className="font-display text-lg font-semibold text-[#16324F] dark:text-stone-100">
              Information users provide
            </h3>
            <p>
              When you register, join a workspace, or use ImpactFlow features, you or your
              organization may provide:
            </p>
            <BulletList
              items={[
                "Name",
                "Email address",
                "Phone number",
                "Organization name and type",
                "Job title and role",
                "Password (stored only as a secure hash — never in plain text)",
                "Profile photo",
                "Survey responses and form submissions",
                "Beneficiary, household, and community records (as configured by your organization)",
                "Project, program, indicator, and MEAL information",
                "Uploaded documents, evidence files, and attachments",
              ]}
            />

            <h3 className="font-display pt-2 text-lg font-semibold text-[#16324F] dark:text-stone-100">
              Automatically collected information
            </h3>
            <p>
              To operate, secure, and improve the service — including the mobile app — we
              may automatically collect:
            </p>
            <BulletList
              items={[
                "Browser type and version",
                "Device type and model",
                "Operating system",
                "IP address",
                "Crash logs and diagnostic data",
                "Usage analytics (feature usage, performance)",
                "Authentication and session logs",
                "API request logs",
                "Device identifiers used for field-device registration and sync",
                "Offline sync metadata (timestamps, conflict markers, payload sizes)",
              ]}
            />

            <h3 className="font-display pt-2 text-lg font-semibold text-[#16324F] dark:text-stone-100">
              Location data
            </h3>
            <p>
              GPS or approximate location is collected <strong>only</strong> when an
              organization enables location capture for surveys, field registrations, or
              evidence geotagging, and when the user grants device permission. Location is
              not collected continuously in the background for advertising.
            </p>

            <h3 className="font-display pt-2 text-lg font-semibold text-[#16324F] dark:text-stone-100">
              Photos and camera
            </h3>
            <p>
              Camera and photo library access are used for evidence collection and
              documentation (for example attaching images to field records). ImpactFlow
              does not access the camera or photo library without an explicit user action
              and the required device permission.
            </p>

            <h3 className="font-display pt-2 text-lg font-semibold text-[#16324F] dark:text-stone-100">
              Files
            </h3>
            <p>
              Organizations may upload attachments such as reports, spreadsheets, PDFs, and
              media. These files are stored in association with the customer tenant and
              governed by that organization’s access controls.
            </p>
          </SectionCard>

          <SectionCard id="how-information-is-used" title="3. How Information Is Used">
            <p>We use information to provide and operate ImpactFlow, including:</p>
            <BulletList
              items={[
                "Authentication and account security",
                "Workspace and tenant creation",
                "Strict tenant isolation between organizations",
                "Reporting, dashboards, and exports",
                "Notifications (in-app and email)",
                "Mobile and web synchronization",
                "Security monitoring and abuse prevention",
                "AI assistance features (when enabled for your plan)",
                "Customer support",
                "Platform reliability and product improvement",
                "Billing, invoicing, and subscription management",
                "Legal compliance and responding to lawful requests",
              ]}
            />
          </SectionCard>

          <SectionCard id="ai-services" title="4. AI Services">
            <p>
              ImpactFlow includes optional AI-powered features (for example AI Copilot).
              Depending on your plan and configuration, AI may assist with:
            </p>
            <BulletList
              items={[
                "Report generation and drafting",
                "Summaries of program or survey content",
                "Risk detection and anomaly suggestions",
                "Workflow suggestions",
                "Knowledge search across permitted organization content",
              ]}
            />
            <p>
              AI <strong>never</strong> silently changes organization data. Suggestions and
              generated text should always be reviewed by authorized users before they are
              relied upon for donor reporting, decisions, or publication.
            </p>
            <p>
              We do not sell customer data. Where AI processing uses subprocessors, it is
              performed under contractual safeguards consistent with this policy and
              applicable data-protection law.
            </p>
          </SectionCard>

          <SectionCard id="offline-data" title="5. Offline Data Collection">
            <p>
              ImpactFlow Field may store survey forms, tasks, and captured responses in
              encrypted local storage on the device while offline. When connectivity is
              restored, data synchronizes to your organization’s workspace over HTTPS.
            </p>
            <p>
              Organizations control their own field data, collector assignments, and
              retention practices. Users should protect devices with OS-level locks and
              follow their organization’s field-security procedures.
            </p>
          </SectionCard>

          <SectionCard id="cookies" title="6. Cookies">
            <p>We use cookies and similar technologies for:</p>
            <BulletList
              items={[
                "Authentication and session continuity",
                "Security (for example CSRF or session integrity where applicable)",
                "Analytics that help us understand product usage",
                "Preference storage (such as theme or locale)",
              ]}
            />
            <p>
              You may disable cookies in your browser. Some features — especially sign-in
              and secure session management — may not work correctly without essential
              cookies.
            </p>
          </SectionCard>

          <SectionCard id="how-data-is-shared" title="7. How Data Is Shared">
            <p className="rounded-xl border border-[#D9E8B8] bg-[#F4F7EF] px-4 py-3 text-[#2F5D3A] dark:border-stone-700 dark:bg-stone-900 dark:text-teal-200">
              ImpactFlow never sells customer data.
            </p>
            <p>We share information only as needed with:</p>
            <BulletList
              items={[
                "Payment providers (for example Paystack) to process subscriptions",
                "Email delivery providers for transactional messages",
                "Cloud infrastructure and storage providers that host the platform",
                "Customer-requested integrations and connectors enabled by your organization",
                "Legal authorities when required by applicable law or valid legal process",
              ]}
            />
            <p>
              Service providers are bound by contractual obligations to process data only
              for specified purposes and to protect it appropriately.
            </p>
          </SectionCard>

          <SectionCard id="third-party-services" title="8. Third-Party Services">
            <p>
              Depending on configuration, ImpactFlow may rely on third-party services such
              as:
            </p>
            <BulletList
              items={[
                "Paystack — payment processing",
                "Google Play — Android distribution and related platform services",
                "Google Maps or map providers — when location maps are enabled",
                "Cloud object storage — file and evidence storage",
                "Email services (for example Resend / SMTP providers)",
                "Analytics providers — product telemetry (where enabled)",
              ]}
            />
            <p>
              Each provider maintains its own privacy policy and terms. We encourage you to
              review those policies. Enabling an optional integration may transmit relevant
              data to that provider under your organization’s instruction.
            </p>
          </SectionCard>

          <SectionCard id="security" title="9. Security">
            <p>
              We apply enterprise SaaS security controls designed to protect customer
              workspaces, including:
            </p>
            <BulletList
              items={[
                "HTTPS / TLS for data in transit",
                "Encryption for sensitive secrets and appropriate data at rest",
                "Password hashing (one-way cryptographic hashes)",
                "Multi-tenant isolation by organization",
                "Role-based access control (RBAC)",
                "Audit logs for sensitive administrative actions",
                "API authentication (tokens / API keys as configured)",
                "Hardened cloud infrastructure practices",
                "Operational backups according to platform policies",
              ]}
            />
            <p>
              No method of transmission or storage is perfectly secure. Organizations
              should apply least-privilege roles, MFA where available, and sound device
              hygiene for field staff.
            </p>
          </SectionCard>

          <SectionCard id="data-retention" title="10. Data Retention">
            <p>
              <strong>Organizations own their program and field data</strong> within their
              ImpactFlow tenant. We retain account and workspace data while a subscription
              (including trial) remains active and as needed to provide the service.
            </p>
            <p>
              After cancellation or deletion requests, we delete or anonymize personal data
              within a reasonable period, subject to legal retention duties, security
              logs, and backup expiry cycles. Organizations may request permanent deletion
              of a workspace subject to verification and any contractual notice periods.
            </p>
          </SectionCard>

          <SectionCard id="user-rights" title="11. User Rights">
            <p>
              Subject to applicable law (including GDPR and the Kenya Data Protection Act),
              you may request:
            </p>
            <BulletList
              items={[
                "Access to personal data we hold about you",
                "Correction of inaccurate personal data",
                "Deletion of personal data",
                "Export / portability of personal data",
                "Restriction of processing",
                "Objection to certain processing",
              ]}
            />
            <p>
              Organization-controlled beneficiary or MEAL records are typically handled by
              your organization’s administrator first. You may also contact us at{" "}
              <a
                className="font-medium text-[#0F766E] underline-offset-2 hover:underline"
                href="mailto:chris@impactflow.space"
              >
                chris@impactflow.space
              </a>
              .
            </p>
          </SectionCard>

          <SectionCard id="international-transfers" title="12. International Transfers">
            <p>
              Customer data may be processed in secure cloud infrastructure located outside
              your country of establishment where permitted by law. Where required, we use
              appropriate safeguards (such as contractual clauses and provider
              certifications) for cross-border transfers.
            </p>
          </SectionCard>

          <SectionCard id="children" title="13. Children">
            <p>
              ImpactFlow is an enterprise workplace product and is not directed to
              children. Users must be at least 18 years old, or authorized employees or
              contractors of a customer organization acting in a professional capacity.
            </p>
            <p>
              If organizations collect information about minors as part of program
              delivery, they are responsible for a lawful basis, consent or parental
              safeguards, and donor/regulatory compliance.
            </p>
          </SectionCard>

          <SectionCard id="government" title="14. Government Organizations">
            <p>
              Government and public-sector customers remain responsible for complying with
              their own national procurement, classification, retention, and data-protection
              rules. ImpactFlow provides technical and organizational measures; agencies
              must configure roles, retention, and field collection settings to meet their
              mandates.
            </p>
          </SectionCard>

          <SectionCard id="data-protection" title="15. Data Protection">
            <p>
              We design ImpactFlow with privacy and security principles aligned to:
            </p>
            <BulletList
              items={[
                "GDPR principles (lawfulness, fairness, transparency, purpose limitation, minimization, accuracy, storage limitation, integrity & confidentiality, accountability)",
                "Kenya Data Protection Act, 2019",
                "POPIA-aligned principles of lawful processing and security safeguards",
                "Industry security best practices for multi-tenant SaaS",
              ]}
            />
            <p>
              Customers (controllers) determine much of the purpose and means of processing
              program data; StemCloud Technologies acts as a processor / operator for
              platform hosting except where we determine purposes for our own account and
              billing data.
            </p>
          </SectionCard>

          <SectionCard id="policy-updates" title="16. Policy Updates">
            <p>
              We may update this Privacy Policy to reflect product, legal, or operational
              changes. Material changes will be communicated through the product, email, or
              a notice on this page. The <strong>Last Updated</strong> date at the top of
              this page shows when the policy was most recently revised ({LAST_UPDATED}).
            </p>
          </SectionCard>

          <SectionCard id="contact" title="17. Contact">
            <p>
              For privacy requests, security concerns, or data-protection inquiries:
            </p>
            <dl className="mt-2 space-y-3 rounded-xl border border-[#E8E2D6] bg-[#F7F4EC]/60 p-4 dark:border-stone-800 dark:bg-stone-900/50">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[#7A7268]">
                  Company
                </dt>
                <dd className="font-medium text-[#16324F] dark:text-stone-100">{COMPANY}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[#7A7268]">
                  Support email
                </dt>
                <dd>
                  <a
                    className="font-medium text-[#0F766E] underline-offset-2 hover:underline"
                    href="mailto:chris@impactflow.space"
                  >
                    chris@impactflow.space
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[#7A7268]">
                  Website
                </dt>
                <dd>
                  <a
                    className="font-medium text-[#0F766E] underline-offset-2 hover:underline"
                    href="https://impactflow.space"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    https://impactflow.space
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-[#7A7268]">
                  Support portal
                </dt>
                <dd>
                  <a
                    className="font-medium text-[#0F766E] underline-offset-2 hover:underline"
                    href="https://impactflow.space/contact"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    https://impactflow.space/contact
                  </a>
                </dd>
              </div>
            </dl>
          </SectionCard>
        </article>
      </main>

      <footer className="no-print border-t border-[#E8E2D6] bg-[#FFFEFB] dark:border-stone-800 dark:bg-stone-950">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-center md:justify-between md:px-8">
          <div className="inline-flex items-center gap-2.5">
            <BrandLogo size={36} />
            <span className="font-display text-lg font-semibold text-[#16324F] dark:text-stone-100">
              ImpactFlow
            </span>
          </div>
          <nav className="flex flex-wrap gap-5 text-sm text-[#5A534B] dark:text-stone-400">
            <Link href="/privacy" className="hover:text-[#16324F] dark:hover:text-stone-200">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-[#16324F] dark:hover:text-stone-200">
              Terms of Service
            </Link>
            <a href="#cookies" className="hover:text-[#16324F] dark:hover:text-stone-200">
              Cookie Policy
            </a>
            <a href="#security" className="hover:text-[#16324F] dark:hover:text-stone-200">
              Security
            </a>
            <a
              href="https://impactflow.space/contact"
              className="hover:text-[#16324F] dark:hover:text-stone-200"
              target="_blank"
              rel="noopener noreferrer"
            >
              Contact
            </a>
            <a
              href="https://impactflow.space"
              className="hover:text-[#16324F] dark:hover:text-stone-200"
              target="_blank"
              rel="noopener noreferrer"
            >
              Documentation
            </a>
          </nav>
        </div>
        <div className="border-t border-[#E8E2D6]/80 px-5 py-4 text-center text-xs text-[#8A8278] dark:border-stone-800 dark:text-stone-500 md:px-8">
          © {new Date().getFullYear()} {COMPANY}. ImpactFlow privacy practices for web and
          mobile.
        </div>
      </footer>

    </div>
  );
}
