"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import type { Citation } from "@/lib/api";

/** Map a citation type to an in-app route when no explicit href is given. */
function inferHref(citation: Citation): string | null {
  if (citation.href) return citation.href;
  const byType: Record<string, string> = {
    knowledge: "/app/knowledge",
    program: `/app/programs/${citation.id}`,
    project: `/app/projects/${citation.id}`,
    grant: "/app/grants",
    donor: "/app/donors",
    indicator: "/app/indicators",
    task: "/app/tasks",
    report: "/app/reports",
    evidence: "/app/evidence",
    prediction: "/app/predictions",
    beneficiary: "/app/beneficiaries",
  };
  return byType[citation.type] ?? null;
}

export function CitationChips({ citations }: { citations?: Citation[] }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {citations.map((citation, idx) => {
        const href = inferHref(citation);
        const inner = (
          <>
            <FileText className="h-3 w-3 opacity-70" />
            <span className="truncate">{citation.label}</span>
          </>
        );
        const className =
          "inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 text-xs font-medium text-stone-600 transition-colors hover:border-teal-300 hover:text-teal-800 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300 dark:hover:text-teal-300";

        if (!href) {
          return (
            <span
              key={`${citation.type}-${citation.id}-${idx}`}
              className={className}
              title={`${citation.type}: ${citation.label}`}
            >
              {inner}
            </span>
          );
        }
        const internal = href.startsWith("/");
        return internal ? (
          <Link
            key={`${citation.type}-${citation.id}-${idx}`}
            href={href}
            className={className}
            title={`${citation.type}: ${citation.label}`}
          >
            {inner}
          </Link>
        ) : (
          <a
            key={`${citation.type}-${citation.id}-${idx}`}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={className}
            title={`${citation.type}: ${citation.label}`}
          >
            {inner}
          </a>
        );
      })}
    </div>
  );
}
