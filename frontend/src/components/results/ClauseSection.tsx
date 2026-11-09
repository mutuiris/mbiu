"use client";

import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import React, { useState, type ReactNode } from "react";

import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";
import type { GroupedResults } from "@/lib/report";

import { Button, Fold, ReportCard } from "./ui";

type Filter = "all" | OutcomeTone;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All checked" },
  { value: "worth_asking_about", label: "Worth inquiry" },
  { value: "unusual", label: "Unusual" },
  { value: "typical", label: "Typical" },
  { value: "cannot_compare", label: "Couldn't compare" },
];

export interface ClauseSectionProps {
  grouped: GroupedResults;
  renderCard: (result: ClauseResult, index: number) => ReactNode;
  /** Cards for clauses that failed for a real error (not the time budget). */
  failedCards: ReactNode[];
  /** Readable names of clauses not checked yet. */
  notCheckedNames: string[];
  onCheckRest?: () => void;
  /** The clause the artist jumped to; its fold opens and the filter resets to show it. */
  selectedClauseId?: string | null;
}

const rowClass =
  "flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-[#e9dec9] py-2 text-[0.92rem] text-mbiu-ink dark:border-white/10 dark:text-[#F4EFE6]";

export function ClauseSection({
  grouped,
  renderCard,
  failedCards,
  notCheckedNames,
  onCheckRest,
  selectedClauseId = null,
}: ClauseSectionProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const has = (list: ClauseResult[]) => !!selectedClauseId && list.some((r) => r.clause_id === selectedClauseId);
  // A jump to a clause goes back to the full list, so a filter never hides it
  const [lastSelected, setLastSelected] = useState(selectedClauseId);
  if (selectedClauseId !== lastSelected) {
    setLastSelected(selectedClauseId);
    if (selectedClauseId && filter !== "all") setFilter("all");
  }
  const total = grouped.cards.length + grouped.standard.length + grouped.cannotCompare.length;
  if (total === 0 && failedCards.length === 0 && notCheckedNames.length === 0) return null;

  const countFor = (f: Filter) => (f === "all" ? total : grouped.counts[f]);
  const filtered =
    filter === "all"
      ? grouped.cards
      : [...grouped.cards, ...grouped.standard, ...grouped.cannotCompare].filter(
          (r) => outcomeLabel(r.comparison).tone === filter,
        );

  return (
    <ReportCard aria-labelledby="clauses-title">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="clauses-title" className="font-serif text-[1.3rem] font-medium leading-tight text-mbiu-ink dark:text-[#F6F2E9]">
          Clause by clause
        </h2>
        <span className="text-[0.85rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">Most important first</span>
      </div>

      {total > 0 && (
        <ToggleGroup
          value={[filter]}
          onValueChange={(value) => setFilter((value[0] as Filter | undefined) ?? "all")}
          aria-label="Show clauses by result"
          className="mt-3 flex flex-wrap gap-2"
        >
          {FILTERS.filter((f) => countFor(f.value) > 0).map((f) => (
            <Toggle
              key={f.value}
              value={f.value}
              className="report-press min-h-11 rounded-full px-4 text-[0.88rem] font-semibold text-mbiu-ink shadow-[inset_0_0_0_1px_rgba(22,26,38,0.18)] data-[pressed]:bg-mbiu-ink data-[pressed]:text-white data-[pressed]:shadow-none dark:text-[#F4EFE6] dark:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.22)] dark:data-[pressed]:bg-[#F4EFE6] dark:data-[pressed]:text-mbiu-ink"
            >
              {f.label} · {countFor(f.value)}
            </Toggle>
          ))}
        </ToggleGroup>
      )}

      <div key={filter} className="report-crossfade mt-4 flex flex-col gap-3 sm:gap-4">
        {filtered.map((r, i) => renderCard(r, i))}
      </div>

      {filter === "all" && (
        <div className="mt-4">
          {grouped.standard.length > 0 && (
            <div className={rowClass}>
              <Fold
                summary={`${grouped.standard.length} standard and boilerplate ${grouped.standard.length === 1 ? "clause" : "clauses"}`}
                className="w-full"
                forceOpen={has(grouped.standard)}
              >
                <div className="flex flex-col gap-4 pb-3 pt-1">{grouped.standard.map((r, i) => renderCard(r, i))}</div>
              </Fold>
            </div>
          )}
          {grouped.cannotCompare.length > 0 && (
            <div className={rowClass}>
              <Fold
                summary={`${grouped.cannotCompare.length} ${grouped.cannotCompare.length === 1 ? "clause" : "clauses"} with no usual contract to compare`}
                className="w-full"
                forceOpen={has(grouped.cannotCompare)}
              >
                <div className="flex flex-col gap-4 pb-3 pt-1">{grouped.cannotCompare.map((r, i) => renderCard(r, i))}</div>
              </Fold>
            </div>
          )}
          {failedCards.length > 0 && <div className="flex flex-col gap-3 border-t border-[#e9dec9] py-3 dark:border-white/10">{failedCards}</div>}
          {notCheckedNames.length > 0 && (
            <div className={rowClass}>
              <Fold summary={`${notCheckedNames.length} ${notCheckedNames.length === 1 ? "clause" : "clauses"} not checked yet`} className="min-w-0 flex-1">
                <p className="text-[0.85rem] text-mbiu-ink/65 dark:text-[#b9c1c5]">
                  Mbiu checked the most important clauses first. These are mostly definitions and signatures.
                </p>
                <ul className="mt-2 columns-1 pb-2 text-[0.85rem] text-mbiu-ink/80 sm:columns-2 dark:text-[#d6dadc]">
                  {notCheckedNames.map((n, i) => (
                    <li key={`${n}-${i}`} className="break-inside-avoid py-0.5">
                      {n}
                    </li>
                  ))}
                </ul>
              </Fold>
              {onCheckRest && <Button onClick={onCheckRest}>Check them</Button>}
            </div>
          )}
        </div>
      )}
    </ReportCard>
  );
}
