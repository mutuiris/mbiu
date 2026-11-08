"use client";

import React, { useState } from "react";

import type { Ask } from "@/lib/api/generated/types.gen";
import { displayNumber, mergeAsks } from "@/lib/report";

import { Button, ReportCard } from "./ui";

type Lookup = ReadonlyMap<string, { number?: string | null; heading?: string | null; pages?: number[] }>;

export interface QuestionsToAskProps {
  asks: readonly Ask[];
  clauseLookup: Lookup;
  onView: (clauseId: string) => void;
}

const joinAnd = (items: string[]) =>
  items.length <= 1 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

function sourceLine(clauseIds: string[], lookup: Lookup): string | null {
  const numbers = clauseIds.map((id) => displayNumber(lookup.get(id)?.number)).filter((n): n is string => !!n);
  const page = clauseIds.map((id) => lookup.get(id)?.pages?.[0]).find((p) => p != null);
  const parts = [numbers.length ? `Clause ${joinAnd(numbers)}` : null, page != null ? `Page ${page}` : null];
  return parts.filter(Boolean).join(" · ") || null;
}

export function QuestionsToAsk({ asks, clauseLookup, onView }: QuestionsToAskProps) {
  const [copied, setCopied] = useState(false);
  const merged = mergeAsks(asks);
  if (merged.length === 0) return null;

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(merged.map((m, i) => `${i + 1}. ${m.question}`).join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <ReportCard aria-labelledby="questions-title">
      <div className="flex items-start justify-between gap-3">
        <h2
          id="questions-title"
          className="font-serif text-[1.3rem] font-medium leading-tight text-mbiu-ink dark:text-[#F6F2E9]"
        >
          Questions to ask before you sign
        </h2>
        <Button onClick={copyAll} aria-live="polite">
          {copied ? "Copied" : "Copy all"}
        </Button>
      </div>
      <ol className="mt-3">
        {merged.map((m, index) => {
          const source = sourceLine(m.clauseIds, clauseLookup);
          return (
            <li
              key={m.question}
              className="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-start gap-3 border-t border-[#e9dec9] py-3 dark:border-white/10"
            >
              <span
                aria-hidden="true"
                className="mt-0.5 grid h-6 w-6 place-items-center rounded-full bg-mbiu-ink text-[0.75rem] font-bold text-white dark:bg-[#F4EFE6] dark:text-mbiu-ink"
              >
                {index + 1}
              </span>
              <div className="min-w-0">
                <p className="break-words text-[0.98rem] leading-snug text-mbiu-ink dark:text-[#F4EFE6]">{m.question}</p>
                {source && <p className="mt-1 text-[0.8rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">{source}</p>}
              </div>
              {m.clauseIds[0] && (
                <button
                  type="button"
                  onClick={() => onView(m.clauseIds[0])}
                  className="report-press min-h-11 px-1 text-[0.88rem] font-semibold text-mbiu-indigo underline underline-offset-4 dark:text-[#a9b0ff]"
                >
                  View
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </ReportCard>
  );
}
