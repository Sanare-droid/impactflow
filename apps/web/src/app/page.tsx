import Image from "next/image";
import Link from "next/link";
import { APP_NAME } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";

const NAV = [
  { href: "#about", label: "About" },
  { href: "#work", label: "What we help" },
  { href: "/pricing", label: "Pricing" },
  { href: "#stories", label: "Stories" },
  { href: "#reach", label: "Reach" },
];

const PRICING_TEASER = [
  { name: "Free Trial", blurb: "14 days · surveys, mobile, basic dashboards" },
  { name: "Starter", blurb: "KES 7,500/mo · field teams & basic AI" },
  { name: "Professional", blurb: "KES 20,000/mo · AI, workflows, white-label" },
  { name: "Enterprise", blurb: "KES 60,000/mo · unlimited scale & SSO" },
];

const FOCUS = [
  {
    title: "Healthy communities",
    body: "Track nutrition, WASH, and health outcomes with evidence teams can trust in the field.",
    icon: (
      <path
        d="M8 11c2.5-4 7.5-4 10 0 1.2 1.9.8 4.4-1 5.7L13 21l-4-4.3C7.2 15.4 6.8 12.9 8 11Z"
        stroke="currentColor"
        strokeWidth="1.6"
        fill="none"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Learning & education",
    body: "See who is reached, who is learning, and where classrooms still need support.",
    icon: (
      <path
        d="M4 8.5 13 4l9 4.5L13 13 4 8.5Zm0 0V16m18-7.5V16M8 11.2v5.1c0 .9 2.2 2.2 5 2.2s5-1.3 5-2.2v-5.1"
        stroke="currentColor"
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Clean water",
    body: "Follow pumps, repairs, and household access without drowning in spreadsheets.",
    icon: (
      <path
        d="M13 3.5S7 10 7 14.2a6 6 0 0 0 12 0C19 10 13 3.5 13 3.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        fill="none"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Care & response",
    body: "Keep casework, referrals, and urgent follow-ups visible across every site.",
    icon: (
      <>
        <path
          d="M13 6v14M6 13h14"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <rect
          x="4.5"
          y="4.5"
          width="17"
          height="17"
          rx="4"
          stroke="currentColor"
          strokeWidth="1.6"
          fill="none"
        />
      </>
    ),
  },
];

const STORIES = [
  {
    name: "Hope Network",
    place: "East Africa",
    quote:
      "We stopped rebuilding the same donor table every quarter. Field officers update once — leadership finally sees the same truth.",
    image:
      "https://images.unsplash.com/photo-1509099836639-18ba1795216d?auto=format&fit=crop&w=800&q=80",
  },
  {
    name: "Riverlight Foundation",
    place: "South Asia",
    quote:
      "Indicators used to live in five tools. ImpactFlow gave our team one place to collect, check, and share.",
    image:
      "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=800&q=80",
  },
  {
    name: "Coastal Alliance",
    place: "West Africa",
    quote:
      "Donors ask harder questions. We answer with photos, GPS notes, and numbers that match — not slide-deck guesses.",
    image:
      "https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=800&q=80",
  },
];

function Brush({
  className,
  color = "#E4B23C",
}: {
  className?: string;
  color?: string;
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 220 28"
      fill="none"
      aria-hidden
    >
      <path
        d="M4 18c28-12 56-14 92-8 34 6 62 8 98 2 8-1 18-3 22-4"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        opacity="0.85"
      />
    </svg>
  );
}

export default function HomePage() {
  return (
    <div className="landing-root min-h-screen bg-[#FFFEFB] text-[#1C1A17]">
      <header className="relative z-20 mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-5 md:px-8">
        <Link href="/" className="inline-flex items-center gap-2.5">
          <BrandLogo size={42} priority />
          <span className="font-display text-2xl font-semibold tracking-tight text-[#16324F]">
            ImpactFlow
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-[#3F3A34] md:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="transition hover:text-[#16324F]"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/login"
            className="hidden text-sm font-medium text-[#3F3A34] transition hover:text-[#16324F] sm:inline"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="rounded-md bg-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#142238]"
          >
            Start free
          </Link>
        </div>
      </header>

      <main>
        {/* Hero — brand + one promise + CTAs + dominant portrait */}
        <section className="relative overflow-hidden border-b border-[#E8E2D6]/120">
          <div
            className="pointer-events-none absolute -left-16 top-24 h-64 w-64 rounded-full opacity-40 blur-2xl"
            style={{
              background:
                "radial-gradient(circle, #F0D56A 0%, transparent 70%)",
            }}
          />
          <div
            className="pointer-events-none absolute right-10 top-10 h-72 w-72 opacity-30"
            style={{
              background:
                "radial-gradient(circle at 40% 40%, #7CB51855, transparent 65%)",
            }}
          />

          <div className="relative mx-auto grid min-h-[min(88vh,820px)] w-full max-w-6xl items-center gap-10 px-5 pb-16 pt-6 md:grid-cols-[1.05fr_0.95fr] md:gap-8 md:px-8 md:pb-20">
            <div className="relative z-10 max-w-xl">
              <p className="animate-fade-up text-xs font-semibold uppercase tracking-[0.2em] text-[#5C6B4A]">
                For organizations that change lives
              </p>
              <h1 className="animate-fade-up font-display mt-4 text-[2.65rem] font-semibold leading-[1.08] tracking-tight text-[#16324F] sm:text-5xl md:text-[3.35rem]">
                A clearer picture of the{" "}
                <span className="relative inline-block">
                  lives you change
                  <Brush className="absolute -bottom-2 left-0 w-[110%] animate-brush-in" />
                </span>
                .
              </h1>
              <p className="animate-fade-up mt-6 max-w-md text-base leading-relaxed text-[#4A453E] [animation-delay:80ms] md:text-lg">
                ImpactFlow brings programs, field evidence, and donor reporting
                into one calm workspace — so your team spends less time
                chasing files and more time with the communities you serve.
              </p>
              <div className="animate-fade-up mt-9 flex flex-wrap items-center gap-4 [animation-delay:140ms]">
                <Link
                  href="/register"
                  className="rounded-md bg-[#1B2A4A] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#142238]"
                >
                  Create workspace
                </Link>
                <Link
                  href="#about"
                  className="group inline-flex items-center gap-2 text-sm font-semibold text-[#16324F]"
                >
                  Discover
                  <span
                    aria-hidden
                    className="transition group-hover:translate-x-1"
                  >
                    →
                  </span>
                </Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md md:max-w-none">
              <div className="absolute -left-6 top-8 hidden h-[78%] w-[72%] md:block">
                <svg viewBox="0 0 200 240" className="h-full w-full opacity-25" aria-hidden>
                  <path
                    d="M110 18c28 6 48 34 44 62-3 22-18 34-14 58 4 26-10 48-34 54s-50-12-58-36c-7-22 4-40-2-60-7-24 6-52 30-64 18-9 22-18 34-14Z"
                    fill="#6B8F3C"
                  />
                </svg>
              </div>
              <div className="animate-fade-up relative overflow-hidden rounded-[2px] [animation-delay:100ms]">
                <Image
                  src="https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=1200&q=80"
                  alt="A child smiling outdoors"
                  width={720}
                  height={900}
                  priority
                  className="aspect-[4/5] w-full object-cover"
                />
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#16324F33] via-transparent to-transparent" />
              </div>
              <div className="animate-fade-up absolute -right-2 bottom-10 max-w-[11rem] rotate-1 rounded-full bg-white/95 px-4 py-3 text-center shadow-[0_12px_40px_rgba(22,50,79,0.12)] [animation-delay:220ms] md:right-0 md:max-w-[12.5rem]">
                <p className="font-display text-sm font-semibold leading-snug text-[#16324F]">
                  Evidence that still feels human
                </p>
                <Brush className="mx-auto mt-1 w-20" color="#7CB518" />
              </div>
            </div>
          </div>
        </section>

        {/* Focus areas */}
        <section id="work" className="mx-auto w-full max-w-6xl px-5 py-16 md:px-8 md:py-20">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
            {FOCUS.map((item) => (
              <div
                key={item.title}
                className="group rounded-2xl px-2 py-3 transition hover:bg-[#F3F0E8]"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center text-[#2F5D3A]">
                  <svg viewBox="0 0 26 26" className="h-8 w-8" aria-hidden>
                    {item.icon}
                  </svg>
                </div>
                <h2 className="font-display text-xl font-semibold text-[#16324F]">
                  {item.title}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-[#5A534B]">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Narrative */}
        <section
          id="about"
          className="border-y border-[#E8E2D6]/90 bg-[#FBF8F1]"
        >
          <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 py-16 md:grid-cols-2 md:gap-16 md:px-8 md:py-24">
            <div className="grid grid-cols-2 gap-3">
              <Image
                src="https://images.unsplash.com/photo-1509099836639-18ba1795216d?auto=format&fit=crop&w=700&q=80"
                alt="Community members outdoors"
                width={420}
                height={520}
                className="col-span-1 row-span-2 h-full min-h-[280px] w-full object-cover"
              />
              <Image
                src="https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=600&q=80"
                alt="Hands joined in solidarity"
                width={320}
                height={220}
                className="h-40 w-full object-cover sm:h-48"
              />
              <Image
                src="https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?auto=format&fit=crop&w=600&q=80"
                alt="Volunteer packing supplies"
                width={320}
                height={220}
                className="h-40 w-full object-cover sm:h-48"
              />
            </div>
            <div>
              <h2 className="font-display text-3xl font-semibold leading-tight text-[#16324F] md:text-4xl">
                Built for the quiet work behind every result
              </h2>
              <p className="mt-5 text-base leading-relaxed text-[#4A453E]">
                Your programs already change lives. ImpactFlow is the place
                those stories, numbers, and field notes finally meet — without
                the buzzwords, without another dashboard nobody opens.
              </p>
              <p className="mt-4 text-base leading-relaxed text-[#4A453E]">
                From village visits to board packs, keep one shared record that
                respects the people in the photos as much as the figures in the
                report.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/register"
                  className="rounded-md bg-[#1B2A4A] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#142238]"
                >
                  Start free
                </Link>
                <Link
                  href="/login"
                  className="text-sm font-semibold text-[#16324F] underline-offset-4 hover:underline"
                >
                  Sign in
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing teaser — full catalog lives on /pricing (DB-driven) */}
        <section id="pricing" className="border-t border-[#E8E2D6]/90 bg-[#FFFEFB]">
          <div className="mx-auto w-full max-w-6xl px-5 py-16 md:px-8 md:py-24">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="font-display text-3xl font-semibold text-[#16324F] md:text-4xl">
                Simple plans that grow with your programs
              </h2>
              <p className="mt-4 text-[#5A534B]">
                Every workspace starts with a <strong>14-day Free Trial</strong>. Upgrade with
                Paystack when you need AI, workflows, or white-label — prices in KES from the
                live catalog.
              </p>
            </div>
            <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {PRICING_TEASER.map((plan) => (
                <div
                  key={plan.name}
                  className="flex flex-col border border-[#E8E2D6] bg-white px-5 py-6"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#5C6B4A]">
                    {plan.name}
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-[#5A534B]">{plan.blurb}</p>
                </div>
              ))}
            </div>
            <div className="mt-10 flex flex-wrap justify-center gap-3">
              <Link
                href="/pricing"
                className="inline-flex justify-center rounded-md bg-[#1B2A4A] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#142238]"
              >
                Compare plans
              </Link>
              <Link
                href="/register"
                className="inline-flex justify-center rounded-md border border-[#1B2A4A] px-5 py-2.5 text-sm font-semibold text-[#1B2A4A] hover:bg-[#F7F4EC]"
              >
                Start free trial
              </Link>
            </div>
          </div>
        </section>

        {/* Stories */}
        <section id="stories" className="mx-auto w-full max-w-6xl px-5 py-16 md:px-8 md:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-semibold text-[#16324F] md:text-4xl">
              Learn from teams already{" "}
              <span className="relative inline-block">
                telling the story
                <Brush className="absolute -bottom-1 left-0 w-full" />
              </span>
            </h2>
            <p className="mt-4 text-[#5A534B]">
              Composite portraits of how organizations use ImpactFlow day to day.
            </p>
          </div>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {STORIES.map((story) => (
              <article key={story.name} className="relative pt-2">
                <div className="absolute left-6 top-0 -z-0 h-24 w-24 rounded-full bg-[#D9E8B8]/70 blur-sm" />
                <Image
                  src={story.image}
                  alt=""
                  width={480}
                  height={560}
                  className="relative z-10 aspect-[4/5] w-full object-cover"
                />
                <h3 className="font-display mt-5 text-xl font-semibold text-[#16324F]">
                  {story.name}
                </h3>
                <p className="text-xs font-semibold uppercase tracking-wider text-[#7A7268]">
                  {story.place}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[#4A453E]">
                  {story.quote}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* Reach / stats */}
        <section
          id="reach"
          className="border-t border-[#E8E2D6]/90 bg-[#F7F4EC]"
        >
          <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 py-16 md:grid-cols-2 md:px-8 md:py-24">
            <div>
              <h2 className="font-display text-3xl font-semibold leading-tight text-[#16324F] md:text-4xl">
                Wherever your programs go,{" "}
                <span className="relative inline-block">
                  the record follows
                  <Brush className="absolute -bottom-1 left-0 w-full" color="#7CB518" />
                </span>
              </h2>
              <dl className="mt-10 grid grid-cols-2 gap-8">
                {[
                  { value: "1", label: "shared workspace" },
                  { value: "∞", label: "field sites connected" },
                  { value: "24/7", label: "secure access" },
                  { value: "You", label: "still own your data" },
                ].map((stat) => (
                  <div key={stat.label}>
                    <dt className="font-display text-3xl font-semibold text-[#2F5D3A]">
                      {stat.value}
                    </dt>
                    <dd className="mt-1 text-sm text-[#5A534B]">{stat.label}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="relative mx-auto w-full max-w-md">
              <svg
                viewBox="0 0 420 360"
                className="h-auto w-full"
                role="img"
                aria-label="Stylized map with program markers"
              >
                <defs>
                  <linearGradient id="land" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#8FBF4A" />
                    <stop offset="55%" stopColor="#E4B23C" />
                    <stop offset="100%" stopColor="#D9773A" />
                  </linearGradient>
                </defs>
                <path
                  d="M210 28c46 8 86 42 94 88 6 34-10 58 2 92 12 36-8 72-46 86-40 14-86-6-110-40-18-26-8-52-18-78-12-32 4-72 36-92 22-14 28-36 42-56Z"
                  fill="url(#land)"
                  opacity="0.9"
                />
                <path
                  d="M168 96c18-10 40-6 52 10 8 12 6 28-2 38-10 14-28 16-42 8-16-10-20-36-8-56Z"
                  fill="#FFFEFB"
                  opacity="0.35"
                />
                {[
                  [180, 120],
                  [240, 150],
                  [200, 200],
                  [260, 220],
                  [170, 240],
                ].map(([x, y], i) => (
                  <g key={i}>
                    <circle cx={x} cy={y} r="10" fill="#FFFEFB" opacity="0.9" />
                    <circle cx={x} cy={y} r="4" fill="#16324F" />
                  </g>
                ))}
              </svg>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="relative overflow-hidden">
          <Image
            src="https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=1600&q=80"
            alt=""
            fill
            className="object-cover"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-[#13233F]/72" />
          <div className="pointer-events-none absolute -left-8 top-8 h-24 w-40 bg-[#7CB518]/50 blur-xl" />
          <div className="pointer-events-none absolute -right-6 bottom-6 h-28 w-48 bg-[#E4B23C]/45 blur-xl" />
          <div className="relative mx-auto flex min-h-[320px] w-full max-w-6xl flex-col items-start justify-center gap-6 px-5 py-20 md:px-8">
            <h2 className="font-display max-w-xl text-3xl font-semibold leading-tight text-white md:text-5xl">
              Join teams who measure what matters — and keep the people in
              focus.
            </h2>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/register"
                className="rounded-md bg-[#E4B23C] px-6 py-3 text-sm font-semibold text-[#1C1A17] transition hover:bg-[#F0C45A]"
              >
                Create workspace
              </Link>
              <Link
                href="/login"
                className="rounded-md bg-[#2F5D3A] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#3A7348]"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[#E8E2D6] bg-[#FFFEFB]">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-5 py-10 md:flex-row md:items-center md:justify-between md:px-8">
          <div className="inline-flex items-center gap-2.5">
            <BrandLogo size={36} />
            <span className="font-display text-lg font-semibold text-[#16324F]">
              {APP_NAME}
            </span>
          </div>
          <nav className="flex flex-wrap gap-5 text-sm text-[#5A534B]">
            {NAV.map((item) => (
              <a key={item.href} href={item.href} className="hover:text-[#16324F]">
                {item.label}
              </a>
            ))}
            <Link href="/privacy" className="hover:text-[#16324F]">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-[#16324F]">
              Terms
            </Link>
            <Link href="/login" className="hover:text-[#16324F]">
              Sign in
            </Link>
          </nav>
          <Link
            href="/register"
            className="w-fit rounded-md bg-[#1B2A4A] px-4 py-2.5 text-sm font-semibold text-white"
          >
            Start free
          </Link>
        </div>
        <div className="border-t border-[#E8E2D6]/80 px-5 py-4 text-center text-xs text-[#8A8278] md:px-8">
          © {new Date().getFullYear()} ImpactFlow. Built for people who do the
          work.
        </div>
      </footer>
    </div>
  );
}
