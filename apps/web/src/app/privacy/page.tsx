import type { Metadata } from "next";
import { PrivacyPolicyView } from "./privacy-policy-view";

const siteUrl =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  "https://impactflow.space";

const title = "Privacy Policy";
const description =
  "How ImpactFlow collects, uses, stores, and protects information across our web platform and mobile applications for NGOs, governments, and development partners.";

export const metadata: Metadata = {
  title,
  description,
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    canonical: `${siteUrl}/privacy`,
  },
  openGraph: {
    type: "website",
    url: `${siteUrl}/privacy`,
    title: `${title} · ImpactFlow`,
    description,
    siteName: "ImpactFlow",
    locale: "en_US",
  },
  twitter: {
    card: "summary",
    title: `${title} · ImpactFlow`,
    description,
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebPage",
  name: "ImpactFlow Privacy Policy",
  description,
  url: `${siteUrl}/privacy`,
  dateModified: "2026-07-17",
  isPartOf: {
    "@type": "WebSite",
    name: "ImpactFlow",
    url: siteUrl,
  },
  publisher: {
    "@type": "Organization",
    name: "StemCloud Technologies",
    url: siteUrl,
    email: "chris@impactflow.space",
  },
};

export default function PrivacyPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <PrivacyPolicyView />
    </>
  );
}
