import React from "react";

import type { ClauseFailure, ClauseResult, DocumentPayload } from "@/lib/api/generated/types.gen";
import { readableClauseName } from "@/lib/report";

import { OutcomePill } from "./ui";

interface ClauseListProps {
  document: DocumentPayload;
  resultsByClauseId: Map<string, ClauseResult>;
  failedByClauseId: Map<string, ClauseFailure>;
  selectedClauseId?: string | null;
  onSelectClause?: (clauseId: string) => void;
}

const quietPill =
  "inline-flex shrink-0 whitespace-nowrap rounded-full bg-black/[0.05] px-2.5 py-1 text-[0.75rem] font-bold text-mbiu-ink/60 dark:bg-white/10 dark:text-[#b9c1c5]";

/** Every clause in the contract with its result: the report's index. */
export const ClauseList: React.FC<ClauseListProps> = ({
  document,
  resultsByClauseId,
  failedByClauseId,
  selectedClauseId,
  onSelectClause,
}) => (
  <ul className="pb-2" aria-label="All clauses">
    {document.clauses.map((clause) => {
      const result = resultsByClauseId.get(clause.clause_id);
      const failure = failedByClauseId.get(clause.clause_id);
      return (
        <li key={clause.clause_id} id={`clause-item-${clause.clause_id}`}>
          <button
            type="button"
            onClick={() => onSelectClause?.(clause.clause_id)}
            aria-current={selectedClauseId === clause.clause_id ? "true" : undefined}
            className="report-press flex min-h-11 w-full items-center justify-between gap-3 border-t border-[#e9dec9] py-2 text-left dark:border-white/10"
          >
            <span className="min-w-0 break-words text-[0.9rem] text-mbiu-ink dark:text-[#F4EFE6]">
              {readableClauseName(clause)}
              <span className="ml-2 text-[0.78rem] text-mbiu-ink/50 dark:text-[#b9c1c5]">
                {clause.pages.length === 1 ? "page" : "pages"} {clause.pages.join(", ")}
              </span>
            </span>
            {result ? (
              <OutcomePill comparison={result.comparison} />
            ) : (
              <span className={quietPill}>{failure && failure.reason !== "not_checked" ? "Couldn't check" : "Not checked yet"}</span>
            )}
          </button>
        </li>
      );
    })}
  </ul>
);
