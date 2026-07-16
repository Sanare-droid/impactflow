"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Shield,
  Settings,
  LogOut,
  Moon,
  Sun,
  Building2,
  ScrollText,
  FolderKanban,
  Layers3,
  CheckSquare,
  HandCoins,
  Landmark,
  Wallet,
  Receipt,
  Target,
  GitBranch,
  Network,
  ClipboardCheck,
  Activity,
  UsersRound,
  Home,
  MapPinned,
  FileText,
  BarChart3,
  Map,
  FolderOpen,
  LayoutPanelTop,
  Sparkles,
  BrainCircuit,
  BookOpenText,
  Scroll,
  Store,
  Plug,
  Palette,
} from "lucide-react";
import { useTheme } from "next-themes";
import { APP_NAME } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const nav = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/programs", label: "Programs", icon: Layers3 },
  { href: "/app/projects", label: "Projects", icon: FolderKanban },
  { href: "/app/tasks", label: "Tasks", icon: CheckSquare },
  { href: "/app/donors", label: "Donors", icon: Landmark },
  { href: "/app/grants", label: "Grants", icon: HandCoins },
  { href: "/app/budgets", label: "Budgets", icon: Wallet },
  { href: "/app/finance", label: "Finance", icon: Receipt },
  { href: "/app/theories-of-change", label: "Theory of Change", icon: GitBranch },
  { href: "/app/logframes", label: "Logframes", icon: Network },
  { href: "/app/indicators", label: "Indicators", icon: Target },
  { href: "/app/monitoring", label: "Monitoring", icon: Activity },
  { href: "/app/evaluations", label: "Evaluations", icon: ClipboardCheck },
  { href: "/app/communities", label: "Communities", icon: MapPinned },
  { href: "/app/households", label: "Households", icon: Home },
  { href: "/app/beneficiaries", label: "Beneficiaries", icon: UsersRound },
  { href: "/app/reports", label: "Reports", icon: FileText },
  { href: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/app/dashboards", label: "Dashboards", icon: LayoutPanelTop },
  { href: "/app/maps", label: "Maps", icon: Map },
  { href: "/app/evidence", label: "Evidence", icon: FolderOpen },
  { href: "/app/copilot", label: "AI Copilot", icon: Sparkles },
  { href: "/app/predictions", label: "Predictions", icon: BrainCircuit },
  { href: "/app/narratives", label: "Narratives", icon: Scroll },
  { href: "/app/knowledge", label: "Knowledge", icon: BookOpenText },
  { href: "/app/marketplace", label: "Marketplace", icon: Store },
  { href: "/app/integrations", label: "Integrations", icon: Plug },
  { href: "/app/branding", label: "White label", icon: Palette },
  { href: "/app/users", label: "Users", icon: Users },
  { href: "/app/roles", label: "Roles", icon: Shield },
  { href: "/app/organization", label: "Organization", icon: Building2 },
  { href: "/app/audit", label: "Audit", icon: ScrollText },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-teal-50 via-stone-50 to-stone-100 dark:from-stone-950 dark:via-stone-950 dark:to-teal-950/40">
      <div className="mx-auto flex min-h-screen max-w-[1400px]">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-hidden border-r border-stone-200/70 bg-white/60 p-4 backdrop-blur-xl dark:border-stone-800 dark:bg-stone-950/50 md:flex">
          <Link href="/app" className="mb-6 shrink-0 px-2">
            <div className="font-display text-xl font-semibold tracking-tight text-teal-900 dark:text-teal-100">
              {APP_NAME}
            </div>
            <p className="mt-1 text-xs text-stone-500">MEAL Operating System</p>
          </Link>

          <nav className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto overscroll-contain pr-1 [-ms-overflow-style:auto] [scrollbar-gutter:stable] [scrollbar-width:thin]">
            {nav.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/app" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "bg-teal-700 text-white shadow-sm dark:bg-teal-600"
                      : "text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-3 shrink-0 space-y-2 border-t border-stone-200/80 pt-4 dark:border-stone-800">
            <div className="px-2 text-sm">
              <p className="font-medium text-stone-900 dark:text-stone-100">
                {user?.display_name ||
                  `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim()}
              </p>
              <p className="truncate text-xs text-stone-500">{user?.email}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Toggle theme"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                className="flex-1 justify-start"
                onClick={async () => {
                  await logout();
                  router.push("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </div>
          </div>
        </aside>

        <main className="flex-1 p-4 md:p-8">
          <div className="mb-6 flex items-center justify-between md:hidden">
            <div className="font-display text-lg font-semibold text-teal-900 dark:text-teal-100">
              {APP_NAME}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
