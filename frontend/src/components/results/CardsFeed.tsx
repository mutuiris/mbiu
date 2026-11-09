"use client";

import React from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { ClauseCard, type LinkedClauseItem } from "./ClauseCard";

export interface CardsFeedProps {
  highImpactResults: ClauseResult[];
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
  selectedClauseId: string | null;
  updatedClauseIds: Set<string>;
  getLinkedClausesFor: (clauseId: string, directLinks?: string[]) => LinkedClauseItem[];
  onSelectClause: (clauseId: string) => void;
  onJumpToPdfClause?: (clauseId: string, pageNumber: number) => void;
}

export const CardsFeed: React.FC<CardsFeedProps> = ({
  highImpactResults,
  clauseLookup,
  selectedClauseId,
  updatedClauseIds,
  getLinkedClausesFor,
  onSelectClause,
  onJumpToPdfClause,
}) => {
  return (
    <section
      className="results-cards-feed"
      aria-label="High-Impact Evaluated Clauses"
    >
      {highImpactResults.map((result) => {
        const extra = clauseLookup.get(result.clause_id);
        return (
          <ClauseCard
            key={result.clause_id}
            result={result}
            clauseNumber={extra?.number}
            clauseHeading={extra?.heading}
            isHighlighted={selectedClauseId === result.clause_id}
            isUpdated={updatedClauseIds.has(result.clause_id)}
            linkedClauses={getLinkedClausesFor(result.clause_id, result.linked_clauses)}
            onSelectClause={onSelectClause}
            onJumpToPdfClause={onJumpToPdfClause}
          />
        );
      })}
    </section>
  );
};
