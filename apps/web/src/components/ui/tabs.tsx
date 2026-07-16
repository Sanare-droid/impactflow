"use client";

import { cn } from "@/lib/utils";

export type TabItem = { id: string; label: string };

export function Tabs({
  items,
  active,
  onChange,
  className,
}: {
  items: TabItem[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap gap-1 border-b border-stone-200 dark:border-stone-800",
        className,
      )}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
          className={cn(
            "-mb-px rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors",
            active === item.id
              ? "border-b-2 border-teal-700 text-teal-800 dark:border-teal-400 dark:text-teal-300"
              : "border-b-2 border-transparent text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-100",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
