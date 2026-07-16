import Link from "next/link";
import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  className,
}: {
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-stone-200 px-6 py-10 text-center dark:border-stone-800",
        className,
      )}
    >
      <p className="font-medium text-stone-800 dark:text-stone-100">{title}</p>
      {description ? (
        <p className="mt-1 max-w-sm text-sm text-stone-500">{description}</p>
      ) : null}
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-4 inline-flex rounded-xl bg-teal-700 px-3 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
