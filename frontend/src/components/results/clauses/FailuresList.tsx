"use client";

import React from "react";
import type { ClauseFailure } from "@/lib/api/generated/types.gen";
import { ClauseFailedCard } from "./ClauseFailedCard";

/** Shown when time or the token budget ran out before every clause was checked. */
export function notCheckedMessage(count: number): string {
  const clauses = count === 1 ? "1 clause isn't" : `${count} clauses aren't`;
  return `Mbiu checked the most important clauses first. ${clauses} checked yet.`;
}

export interface FailuresListProps {
  failures: ClauseFailure[];
  notCheckedCount: number;
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
  onRetry: (clauseId: string) => Promise<void> | void;
  retryingClauseId: string | null;
}

export const FailuresList: React.FC<FailuresListProps> = ({
  failures,
  notCheckedCount,
  clauseLookup,
  onRetry,
  retryingClauseId,
}) => {
  return (
    <>
      {notCheckedCount > 0 && (
        <p className="status-alert info" role="status">
          {notCheckedMessage(notCheckedCount)}
        </p>
      )}

      {failures.length > 0 && (
        <section
          className="failed-clauses-section"
          aria-label="Clauses that could not be checked"
        >
          {failures.map((f) => {
            const extra = clauseLookup.get(f.clause_id);
            return (
              <ClauseFailedCard
                key={f.clause_id}
                failure={f}
                clauseNumber={extra?.number}
                clauseHeading={extra?.heading}
                onRetry={onRetry}
                isRetrying={retryingClauseId === f.clause_id}
              />
            );
          })}
        </section>
      )}
    </>
  );
};
