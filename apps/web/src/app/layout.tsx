import type { Metadata } from "next";
import { Manrope, Source_Serif_4 } from "next/font/google";
import { Providers } from "@/providers/providers";
import { APP_NAME } from "@/lib/api";
import "./globals.css";

const body = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
});

const display = Source_Serif_4({
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
    "Enterprise MEAL, grants, and impact operating system for the development sector.",
  applicationName: APP_NAME,
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: APP_NAME,
    title: APP_NAME,
    description:
      "Plan programs, collect field evidence, monitor indicators, and report donor impact from one secure platform.",
  },
  twitter: {
    card: "summary_large_image",
    title: APP_NAME,
    description:
      "MEAL operating system for development organizations worldwide.",
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
