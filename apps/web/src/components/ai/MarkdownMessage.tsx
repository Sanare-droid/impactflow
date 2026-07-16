"use client";

import { Fragment, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Lightweight markdown renderer — intentionally dependency-free.
 * Supports headings, bold, inline code, links, ordered/unordered lists,
 * fenced code blocks, blockquotes, and simple pipe tables. Anything more
 * exotic falls back to plain text so we never render raw HTML.
 */

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  // Tokenise on inline code, bold, and links in priority order.
  const pattern =
    /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(
        <Fragment key={`${keyPrefix}-t${i}`}>
          {text.slice(lastIndex, match.index)}
        </Fragment>,
      );
    }
    const token = match[0];
    if (token.startsWith("`")) {
      nodes.push(
        <code
          key={`${keyPrefix}-c${i}`}
          className="rounded bg-stone-200/70 px-1.5 py-0.5 font-mono text-[0.85em] text-stone-800 dark:bg-stone-800 dark:text-stone-100"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("**")) {
      nodes.push(
        <strong key={`${keyPrefix}-b${i}`} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else {
      const linkMatch = /\[([^\]]+)\]\(([^)]+)\)/.exec(token);
      if (linkMatch) {
        const href = linkMatch[2];
        const internal = href.startsWith("/");
        nodes.push(
          <a
            key={`${keyPrefix}-l${i}`}
            href={href}
            target={internal ? undefined : "_blank"}
            rel={internal ? undefined : "noopener noreferrer"}
            className="font-medium text-teal-700 underline decoration-teal-300 underline-offset-2 hover:text-teal-800 dark:text-teal-300"
          >
            {linkMatch[1]}
          </a>,
        );
      }
    }
    lastIndex = match.index + token.length;
    i += 1;
  }
  if (lastIndex < text.length) {
    nodes.push(
      <Fragment key={`${keyPrefix}-tend`}>{text.slice(lastIndex)}</Fragment>,
    );
  }
  return nodes;
}

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "code"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] }
  | { kind: "table"; header: string[]; rows: string[][] }
  | { kind: "p"; text: string };

function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  const splitRow = (line: string) =>
    line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    // Fenced code block
    if (trimmed.startsWith("```")) {
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        buf.push(lines[i]);
        i += 1;
      }
      i += 1; // skip closing fence
      blocks.push({ kind: "code", text: buf.join("\n") });
      continue;
    }

    // Heading
    const heading = /^(#{1,4})\s+(.*)$/.exec(trimmed);
    if (heading) {
      blocks.push({
        kind: "heading",
        level: heading[1].length,
        text: heading[2],
      });
      i += 1;
      continue;
    }

    // Table (needs a separator row second)
    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      /^\s*\|?[\s:-]*-[\s:|-]*\|?\s*$/.test(lines[i + 1])
    ) {
      const header = splitRow(trimmed);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
        rows.push(splitRow(lines[i]));
        i += 1;
      }
      blocks.push({ kind: "table", header, rows });
      continue;
    }

    // Blockquote
    if (trimmed.startsWith(">")) {
      const buf: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        buf.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ kind: "quote", text: buf.join(" ") });
      continue;
    }

    // Unordered list
    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      blocks.push({ kind: "ul", items });
      continue;
    }

    // Ordered list
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push({ kind: "ol", items });
      continue;
    }

    // Paragraph (consume consecutive non-blank, non-special lines)
    const buf: string[] = [trimmed];
    i += 1;
    while (i < lines.length) {
      const next = lines[i].trim();
      if (
        !next ||
        next.startsWith("```") ||
        next.startsWith("#") ||
        next.startsWith(">") ||
        /^[-*]\s+/.test(next) ||
        /^\d+\.\s+/.test(next) ||
        next.includes("|")
      ) {
        break;
      }
      buf.push(next);
      i += 1;
    }
    blocks.push({ kind: "p", text: buf.join(" ") });
  }

  return blocks;
}

export function MarkdownMessage({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  const blocks = parseBlocks(content);

  return (
    <div className={cn("space-y-3 text-sm leading-relaxed", className)}>
      {blocks.map((block, idx) => {
        const key = `blk-${idx}`;
        switch (block.kind) {
          case "heading": {
            const sizes: Record<number, string> = {
              1: "text-lg",
              2: "text-base",
              3: "text-sm",
              4: "text-sm",
            };
            return (
              <p
                key={key}
                className={cn(
                  "font-display font-semibold tracking-tight text-stone-900 dark:text-stone-50",
                  sizes[block.level] ?? "text-sm",
                )}
              >
                {renderInline(block.text, key)}
              </p>
            );
          }
          case "code":
            return (
              <pre
                key={key}
                className="overflow-x-auto rounded-xl bg-stone-900 p-3 text-xs text-stone-100 dark:bg-black/60"
              >
                <code className="font-mono">{block.text}</code>
              </pre>
            );
          case "quote":
            return (
              <blockquote
                key={key}
                className="border-l-2 border-teal-400 pl-3 text-stone-600 dark:text-stone-300"
              >
                {renderInline(block.text, key)}
              </blockquote>
            );
          case "ul":
            return (
              <ul key={key} className="list-disc space-y-1 pl-5">
                {block.items.map((item, j) => (
                  <li key={`${key}-${j}`}>{renderInline(item, `${key}-${j}`)}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={key} className="list-decimal space-y-1 pl-5">
                {block.items.map((item, j) => (
                  <li key={`${key}-${j}`}>{renderInline(item, `${key}-${j}`)}</li>
                ))}
              </ol>
            );
          case "table":
            return (
              <div key={key} className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-stone-200 dark:border-stone-700">
                      {block.header.map((h, j) => (
                        <th
                          key={`${key}-h${j}`}
                          className="px-2 py-1.5 font-semibold text-stone-700 dark:text-stone-200"
                        >
                          {renderInline(h, `${key}-h${j}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, r) => (
                      <tr
                        key={`${key}-r${r}`}
                        className="border-b border-stone-100 dark:border-stone-800"
                      >
                        {row.map((cell, c) => (
                          <td
                            key={`${key}-r${r}c${c}`}
                            className="px-2 py-1.5 align-top text-stone-600 dark:text-stone-300"
                          >
                            {renderInline(cell, `${key}-r${r}c${c}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          default:
            return (
              <p key={key} className="whitespace-pre-wrap">
                {renderInline(block.text, key)}
              </p>
            );
        }
      })}
    </div>
  );
}
