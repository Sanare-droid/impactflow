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
  Smartphone,
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
  Bell,
  ClipboardList,
  Workflow,
  Gauge,
  Code2,
  CreditCard,
  Rocket,
  HeartPulse,
  type LucideIcon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { APP_NAME, api } from "@/lib/api";
import { BrandLogo } from "@/components/brand-logo";
import { useAuth } from "@/providers/auth-provider";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Plan feature flag required to show this nav item */
  feature?: string;
  /** Only platform admins / superusers */
  platformAdminOnly?: boolean;
};
type NavGroup = { label: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    label: "Workspace",
    items: [
      { href: "/app", label: "Dashboard", icon: LayoutDashboard },
      { href: "/app/notifications", label: "Notifications", icon: Bell },
    ],
  },
  {
    label: "Delivery",
    items: [
      { href: "/app/programs", label: "Programs", icon: Layers3 },
      { href: "/app/projects", label: "Projects", icon: FolderKanban },
      { href: "/app/tasks", label: "Tasks", icon: CheckSquare },
    ],
  },
  {
    label: "Finance",
    items: [
      { href: "/app/donors", label: "Donors", icon: Landmark },
      { href: "/app/grants", label: "Grants", icon: HandCoins },
      { href: "/app/budgets", label: "Budgets", icon: Wallet },
      { href: "/app/finance", label: "Finance", icon: Receipt },
    ],
  },
  {
    label: "MEAL",
    items: [
      { href: "/app/theories-of-change", label: "Theory of Change", icon: GitBranch },
      { href: "/app/logframes", label: "Logframes", icon: Network },
      { href: "/app/indicators", label: "Indicators", icon: Target },
      { href: "/app/monitoring", label: "Monitoring", icon: Activity },
      { href: "/app/evaluations", label: "Evaluations", icon: ClipboardCheck },
      { href: "/app/surveys", label: "Surveys", icon: ClipboardList, feature: "surveys" },
    ],
  },
  {
    label: "Field",
    items: [
      {
        href: "/app/field-operations",
        label: "Field Operations",
        icon: Smartphone,
        feature: "field_ops",
      },
      { href: "/app/communities", label: "Communities", icon: MapPinned },
      { href: "/app/households", label: "Households", icon: Home },
      { href: "/app/beneficiaries", label: "Beneficiaries", icon: UsersRound },
    ],
  },
  {
    label: "Insights",
    items: [
      { href: "/app/executive", label: "Executive", icon: Gauge, feature: "executive" },
      { href: "/app/reports", label: "Reports", icon: FileText },
      { href: "/app/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/app/dashboards", label: "Dashboards", icon: LayoutPanelTop },
      { href: "/app/maps", label: "Maps", icon: Map },
      { href: "/app/evidence", label: "Evidence", icon: FolderOpen },
    ],
  },
  {
    label: "AI",
    items: [
      { href: "/app/copilot", label: "AI Copilot", icon: Sparkles, feature: "ai" },
      { href: "/app/predictions", label: "Predictions", icon: BrainCircuit, feature: "ai" },
      { href: "/app/narratives", label: "Narratives", icon: Scroll, feature: "ai" },
      { href: "/app/knowledge", label: "Knowledge", icon: BookOpenText, feature: "ai" },
    ],
  },
  {
    label: "Platform",
    items: [
      { href: "/app/workflows", label: "Workflows", icon: Workflow, feature: "workflows" },
      { href: "/app/marketplace", label: "Marketplace", icon: Store, feature: "marketplace" },
      {
        href: "/app/integrations",
        label: "Integrations",
        icon: Plug,
        feature: "integrations",
      },
      { href: "/app/developer", label: "Developer", icon: Code2, feature: "api_access" },
      { href: "/app/branding", label: "White label", icon: Palette, feature: "white_label" },
      { href: "/app/onboarding", label: "Onboarding", icon: Rocket },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "/app/users", label: "Users", icon: Users },
      { href: "/app/roles", label: "Roles", icon: Shield },
      { href: "/app/organization", label: "Organization", icon: Building2 },
      { href: "/app/billing", label: "Billing", icon: CreditCard },
      {
        href: "/app/platform/billing",
        label: "Platform billing",
        icon: Landmark,
        platformAdminOnly: true,
      },
      {
        href: "/app/customer-success",
        label: "Success",
        icon: HeartPulse,
        platformAdminOnly: true,
      },
      { href: "/app/ops", label: "Operations", icon: Activity, platformAdminOnly: true },
      { href: "/app/audit", label: "Audit", icon: ScrollText },
      { href: "/app/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { data: unread } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: () => api.notificationsUnreadCount(),
    refetchInterval: 30_000,
  });
  const { data: featuresPayload } = useQuery({
    queryKey: ["features"],
    queryFn: () => api.getFeatures(),
    staleTime: 60_000,
  });
  const isPlatformAdmin = Boolean(user?.is_platform_admin || user?.is_superuser);
  const unreadCount = unread?.unread_count ?? 0;

  const visibleGroups = useMemo(() => {
    const features = featuresPayload?.features ?? {};
    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => {
          if (item.platformAdminOnly && !isPlatformAdmin) return false;
          if (item.feature && features[item.feature] === false) return false;
          // If features not loaded yet, show items (avoid empty nav flash)
          return true;
        }),
      }))
      .filter((g) => g.items.length > 0);
  }, [featuresPayload?.features, isPlatformAdmin]);

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-teal-50 via-stone-50 to-stone-100 dark:from-stone-950 dark:via-stone-950 dark:to-teal-950/40">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="mx-auto flex min-h-screen max-w-[1400px]">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-hidden border-r border-stone-200/70 bg-white/60 p-4 backdrop-blur-xl dark:border-stone-800 dark:bg-stone-950/50 md:flex">
          <Link href="/app" className="mb-6 shrink-0 px-2">
            <BrandLogo
              size={40}
              priority
              withWordmark
              wordmark={APP_NAME}
              wordmarkClassName="text-lg leading-tight"
            />
            <p className="mt-1.5 text-xs text-stone-500">MEAL Operating System</p>
          </Link>

          <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain pr-1 [-ms-overflow-style:auto] [scrollbar-gutter:stable] [scrollbar-width:thin]">
            {visibleGroups.map((group) => (
              <div key={group.label} className="space-y-1">
                <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-stone-400">
                  {group.label}
                </p>
                {group.items.map((item) => {
                  const active =
                    pathname === item.href ||
                    (item.href !== "/app" && pathname.startsWith(item.href));
                  const Icon = item.icon;
                  const showBadge =
                    item.href === "/app/notifications" && unreadCount > 0;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition",
                        active
                          ? "bg-teal-700 text-white shadow-sm"
                          : "text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900",
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0 opacity-80" />
                      <span className="truncate">{item.label}</span>
                      {showBadge ? (
                        <span className="ml-auto rounded-full bg-rose-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                          {unreadCount > 99 ? "99+" : unreadCount}
                        </span>
                      ) : null}
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>

          <div className="mt-4 shrink-0 space-y-2 border-t border-stone-200/70 pt-4 dark:border-stone-800">
            <p className="truncate px-2 text-xs text-stone-500">{user?.email}</p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                className="flex-1"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="flex-1"
                onClick={async () => {
                  await logout();
                  router.push("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </aside>

        <main id="main-content" className="min-w-0 flex-1 p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
