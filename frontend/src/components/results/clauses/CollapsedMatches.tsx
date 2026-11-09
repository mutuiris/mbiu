"use client";

import React, { useState } from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";

export interface CollapsedMatchesProps {
  matches: ClauseResult[];
  clauseLookup?: Map<string, { number?: string | null; heading?: string | null }>;
  onSelectClause?: (clauseId: string) => void;
  selectedClauseId?: string | null;
}

export const CollapsedMatches: React.FC<CollapsedMatchesProps> = ({
  matches,
  clauseLookup,
  onSelectClause,
  selectedClauseId,
}) => {
  const [isManuallyToggled, setIsManuallyToggled] = useState<boolean | null>(null);

  const isSelectedInMatches = Boolean(
    selectedClauseId && matches.some((m) => m.clause_id === selectedClauseId),
  );
  const isOpen = isManuallyToggled !== null ? isManuallyToggled : isSelectedInMatches;

  if (matches.length === 0) return null;

  return (
    <section className="collapsed-matches-container" aria-label="Standard & boilerplate clauses">
      <div
        className="collapsed-matches-header"
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        onClick={() => setIsManuallyToggled(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsManuallyToggled(!isOpen);
          }
        }}
      >
        <div className="matches-summary-left">
          <span className="check-icon" aria-hidden="true">✓</span>
          <span className="matches-summary-text">
            <strong>
              {matches.length} {matches.length === 1 ? "clause is" : "clauses are"} standard &amp; boilerplate
            </strong>
          </span>
        </div>
        <button
          type="button"
          className="matches-toggle-btn"
          aria-label={isOpen ? "Collapse standard clauses" : "Expand standard clauses"}
        >
          {isOpen ? "Hide details" : "View standard clauses"}
        </button>
      </div>

      {isOpen && (
        <ul className="collapsed-matches-list" role="list">
          {matches.map((item) => {
            const extra = clauseLookup?.get(item.clause_id);
            const num = extra?.number ? `Clause ${extra.number}` : `Clause`;
            const heading = extra?.heading || item.headline || "Standard clause";
            const pageStr = `p. ${item.pages.join(", ")}`;
            const isSelected = selectedClauseId === item.clause_id;

            return (
              <li
                key={item.clause_id}
                id={`clause-item-${item.clause_id}`}
                className={`matching-clause-line ${isSelected ? "selected" : ""}`}
                onClick={() => onSelectClause?.(item.clause_id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectClause?.(item.clause_id);
                  }
                }}
              >
                <span className="match-line-badge">Standard</span>
                <span className="match-line-id">{num}</span>
                <span className="match-line-title">{heading}</span>
                <span className="match-line-page">{pageStr}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};
