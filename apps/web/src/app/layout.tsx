import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import { Providers } from "@/providers/providers";
import { APP_NAME } from "@/lib/api";
import "./globals.css";

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
});

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const siteUrl =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: APP_NAME,
    template: `%s · ${APP_NAME}`,
  },
  description:
    "ImpactFlow helps development organizations turn field work into clear evidence for the people and donors who depend on them.",
  applicationName: APP_NAME,
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: APP_NAME,
    title: APP_NAME,
    description:
      "One workspace to plan programs, gather evidence, and show the difference your work makes.",
  },
  twitter: {
    card: "summary_large_image",
    title: APP_NAME,
    description:
      "Show the human impact behind every program — clearly, securely, together.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${body.variable} ${display.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
