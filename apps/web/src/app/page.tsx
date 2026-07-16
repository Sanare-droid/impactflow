import Link from "next/link";
import { APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#081226] text-slate-100">
      <div
        className="pointer-events-none absolute inset-0 opacity-90"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 15% 20%, rgba(59,130,246,0.28), transparent 55%), radial-gradient(ellipse 70% 50% at 85% 10%, rgba(74,222,128,0.22), transparent 50%), radial-gradient(ellipse 50% 40% at 70% 80%, rgba(15,118,110,0.2), transparent 45%)",
        }}
      />
      <div className="pointer-events-none absolute inset-0 animate-soft-pulse bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2248%22 height=%2248%22 viewBox=%220 0 48 48%22><path fill=%22%23ffffff08%22 d=%22M0 47h48v1H0zM47 0v48h1V0z%22/></svg>')]" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/" className="inline-flex items-center gap-2.5">
          <BrandLogo size={40} priority />
          <span className="font-display text-xl font-semibold tracking-tight text-white">
            ImpactFlow
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button
              variant="ghost"
              className="text-slate-200 hover:bg-white/10 hover:text-white"
            >
              Sign in
            </Button>
          </Link>
          <Link href="/register">
            <Button className="bg-emerald-400 text-slate-950 hover:bg-emerald-300">
              Get started
            </Button>
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[78vh] w-full max-w-6xl flex-col justify-center px-6 pb-24 pt-8">
        <p className="animate-fade-up text-sm font-medium uppercase tracking-[0.22em] text-sky-300/80">
          MEAL operating system
        </p>
        <h1 className="animate-fade-up font-display mt-5 max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight text-white md:text-7xl">
          {APP_NAME}
        </h1>
        <p className="animate-fade-up mt-6 max-w-xl text-lg leading-relaxed text-slate-300 [animation-delay:100ms]">
          Plan programs, collect field evidence, monitor indicators, and report
          donor impact — one secure workspace for development organizations
          worldwide.
        </p>
        <div className="animate-fade-up mt-10 flex flex-wrap gap-3 [animation-delay:180ms]">
          <Link href="/register">
            <Button
              size="lg"
              className="bg-emerald-400 text-slate-950 hover:bg-emerald-300"
            >
              Create workspace
            </Button>
          </Link>
          <Link href="/login">
            <Button
              size="lg"
              variant="outline"
              className="border-white/25 bg-white/5 text-white hover:bg-white/10"
            >
              Sign in to workspace
            </Button>
          </Link>
        </div>
        <p className="animate-fade-up mt-14 max-w-2xl text-sm text-slate-400 [animation-delay:260ms]">
          Built for NGOs, foundations, governments, UN agencies, and partners who
          need multi-tenant MEAL, AI assist, and white-label delivery.
        </p>
      </main>
    </div>
  );
}
