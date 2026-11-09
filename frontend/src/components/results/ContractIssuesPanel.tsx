"use client";

import React, { useState } from "react";

import type { ContractIssue } from "@/lib/api/generated/types.gen";
import { readableClauseName } from "@/lib/report";

import { Fold, ReportCard } from "./ui";

export interface ContractIssuesPanelProps {
  issues: ContractIssue[];
  /** Resolves clause numbers, headings and pages by clause_id. */
  clauseLookup?: Map<string, { number?: string | null; heading?: string | null; pages?: number[] }>;
  /** Called when the artist taps "See both". */
  onSelectClause?: (clauseId: string) => void;
}

const KIND_LABEL: Record<ContractIssue["kind"], string> = {
  override: "One clause cancels another",
  conflict: "Two clauses disagree",
};

const FIRST_SHOWN = 3;

// The rules append the disclaimer to every explanation; the panel says it once instead
const withoutDisclaimer = (text: string) => text.replace(/\s*Mbiu reports that one clause[^.]*\./g, "").trim();

export const ContractIssuesPanel: React.FC<ContractIssuesPanelProps> = ({
  issues,
  clauseLookup,
  onSelectClause,
}) => {
  const [showAll, setShowAll] = useState(false);
  if (!issues || issues.length === 0) return null;

  const shown = showAll ? issues : issues.slice(0, FIRST_SHOWN);
  const name = (clauseId: string) => readableClauseName(clauseLookup?.get(clauseId));
  const page = (clauseId: string, index: number, issue: ContractIssue) =>
    clauseLookup?.get(clauseId)?.pages?.[0] ?? issue.pages[index] ?? issue.pages[0];

  return (
    <ReportCard aria-labelledby="clashes-title" data-testid="contract-issues-panel">
      <div className="flex items-baseline justify-between gap-3">
        <h2
          id="clashes-title"
          className="font-serif text-[1.3rem] font-medium leading-tight text-mbiu-ink dark:text-[#F6F2E9]"
        >
          Clauses that clash
        </h2>
        <span className="text-[0.9rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">{issues.length}</span>
      </div>
      <p className="mt-1 text-[0.82rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">
        Mbiu shows where one clause claims to override another. It never decides which a court would apply.
      </p>

      <ul className="mt-3">
        {shown.map((issue, index) => (
          <li
            key={`${issue.clause_ids.join("-")}-${index}`}
            className="border-t border-[#e9dec9] py-3 dark:border-white/10"
          >
            <span className="inline-flex whitespace-nowrap rounded-full bg-mbiu-ink/[0.07] px-2.5 py-1 text-[0.75rem] font-bold text-mbiu-ink dark:bg-white/10 dark:text-[#F4EFE6]">
              {KIND_LABEL[issue.kind]}
            </span>
            <p className="mt-2 break-words text-[0.96rem] leading-snug text-mbiu-ink dark:text-[#F4EFE6]">
              {withoutDisclaimer(issue.explanation)}
            </p>
            <p className="mt-1 break-words text-[0.8rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">
              {issue.clause_ids
                .map((id, i) => {
                  const p = page(id, i, issue);
                  return p != null ? `${name(id)} (page ${p})` : name(id);
                })
                .join(" and ")}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-5">
              {onSelectClause && (
                <button
                  type="button"
                  onClick={() => onSelectClause(issue.clause_ids[0])}
                  className="report-press min-h-11 text-[0.9rem] font-semibold text-mbiu-indigo underline underline-offset-4 dark:text-[#a9b0ff]"
                >
                  See both
                </button>
              )}
              <Fold summary="See the exact words">
                <div className="space-y-2 pb-1 text-[0.88rem] text-mbiu-ink/80 dark:text-[#d6dadc]">
                  {issue.quotes.map((quote, i) => (
                    <blockquote key={i} className="border-l-2 border-[#e9dec9] pl-3 dark:border-white/15">
                      <span className="block text-[0.75rem] font-semibold text-mbiu-ink/55 dark:text-[#b9c1c5]">
                        {name(issue.clause_ids[i])}
                      </span>
                      “{quote}”
                    </blockquote>
                  ))}
                </div>
              </Fold>
            </div>
          </li>
        ))}
      </ul>

      {issues.length > FIRST_SHOWN && !showAll && (
        <div className="flex items-center justify-between border-t border-[#e9dec9] pt-2 text-[0.88rem] text-mbiu-ink/60 dark:border-white/10 dark:text-[#b9c1c5]">
          <span>{issues.length - FIRST_SHOWN} more</span>
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="report-press min-h-11 font-semibold text-mbiu-indigo underline underline-offset-4 dark:text-[#a9b0ff]"
          >
            Show all {issues.length}
          </button>
        </div>
      )}
    </ReportCard>
  );
};
