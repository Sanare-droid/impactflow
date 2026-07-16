import Link from "next/link";
import { APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_20%_20%,#ccfbf1_0%,transparent_35%),radial-gradient(circle_at_80%_0%,#fef3c7_0%,transparent_28%),linear-gradient(180deg,#fafaf9_0%,#f5f5f4_100%)] dark:bg-[radial-gradient(circle_at_20%_20%,#134e4a_0%,transparent_40%),linear-gradient(180deg,#0c0a09_0%,#1c1917_100%)]">
      <div className="pointer-events-none absolute inset-0 animate-soft-pulse bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22 viewBox=%220 0 40 40%22><path fill=%22%2300000020%22 d=%22M0 39h40v1H0zM39 0v40h1V0z%22/></svg>')] opacity-40 dark:opacity-20" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <BrandLogo size={44} priority withWordmark wordmark={APP_NAME} />
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/register">
            <Button>Get started</Button>
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[75vh] w-full max-w-6xl flex-col justify-center px-6 pb-24 pt-10">
        <div className="animate-fade-up mb-8">
          <BrandLogo size={88} priority />
        </div>
        <p className="animate-fade-up text-sm font-medium uppercase tracking-[0.2em] text-teal-800/70 dark:text-teal-200/70">
          Global development OS
        </p>
        <h1 className="animate-fade-up font-display mt-4 max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight text-stone-900 dark:text-stone-50 md:text-7xl">
          {APP_NAME}
        </h1>
        <p className="animate-fade-up mt-6 max-w-xl text-lg text-stone-600 dark:text-stone-300 [animation-delay:120ms]">
          Plan programs, collect field evidence, monitor indicators, and report
          donor impact from one secure, multi-tenant platform.
        </p>
        <div className="animate-fade-up mt-10 flex flex-wrap gap-3 [animation-delay:200ms]">
          <Link href="/register">
            <Button size="lg">Create organization</Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline">
              Sign in to workspace
            </Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
