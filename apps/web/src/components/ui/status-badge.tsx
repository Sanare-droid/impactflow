import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  draft: "bg-stone-100 text-stone-700 dark:bg-stone-900 dark:text-stone-300",
  planning: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  planned: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  pipeline: "bg-violet-50 text-violet-800 dark:bg-violet-950 dark:text-violet-200",
  prospect: "bg-violet-50 text-violet-800 dark:bg-violet-950 dark:text-violet-200",
  awarded: "bg-cyan-50 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-200",
  approved: "bg-cyan-50 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-200",
  active: "bg-teal-50 text-teal-800 dark:bg-teal-950 dark:text-teal-200",
  in_progress: "bg-sky-50 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  on_hold: "bg-orange-50 text-orange-800 dark:bg-orange-950 dark:text-orange-200",
  blocked: "bg-rose-50 text-rose-800 dark:bg-rose-950 dark:text-rose-200",
  completed: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  done: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  posted: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  locked: "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
  todo: "bg-stone-100 text-stone-700 dark:bg-stone-900 dark:text-stone-300",
  cancelled: "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  rejected: "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  closed: "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
  archived: "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
  inactive: "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
  submitted: "bg-sky-50 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  verified: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  retired: "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
  draft_report: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  achieved: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  missed: "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-1 text-xs font-medium capitalize",
        tones[status] ?? tones.draft,
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
