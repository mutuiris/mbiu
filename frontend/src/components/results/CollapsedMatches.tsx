import React, { useState } from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";

interface CollapsedMatchesProps {
  matches: ClauseResult[];
  clauseLookup?: Map<string, { number?: string | null; heading?: string | null }>;
}

export const CollapsedMatches: React.FC<CollapsedMatchesProps> = ({
  matches,
  clauseLookup,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (matches.length === 0) return null;

  return (
    <section className="collapsed-matches-container" aria-label="Typical clauses">
      <div
        className="collapsed-matches-header"
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
      >
        <div className="matches-summary-left">
          <span className="check-icon" aria-hidden="true">✓</span>
          <span className="matches-summary-text">
            <strong>{matches.length} {matches.length === 1 ? "clause is" : "clauses are"} typical</strong>
          </span>
        </div>
        <button
          type="button"
          className="matches-toggle-btn"
          aria-label={isOpen ? "Collapse typical clauses" : "Expand typical clauses"}
        >
          {isOpen ? "Hide details" : "View typical clauses"}
        </button>
      </div>

      {isOpen && (
        <ul className="collapsed-matches-list" role="list">
          {matches.map((item) => {
            const extra = clauseLookup?.get(item.clause_id);
            const num = extra?.number ? `Clause ${extra.number}` : `Clause`;
            const heading = extra?.heading || item.headline || "Standard clause";
            const pageStr = `p. ${item.pages.join(", ")}`;

            return (
              <li key={item.clause_id} className="matching-clause-line">
                <span className="match-line-badge">Matches standard</span>
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
