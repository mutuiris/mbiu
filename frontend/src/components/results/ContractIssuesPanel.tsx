"use client";

import React from "react";
import type { ContractIssue } from "@/lib/api/generated/types.gen";

export interface ContractIssuesPanelProps {
  issues: ContractIssue[];
  /**
   * Fast lookup to resolve clause numbers and headings by clause_id.
   */
  clauseLookup?: Map<string, { number?: string | null; heading?: string | null; pages?: number[] }>;
  /**
   * Callback invoked when a user taps a clause link to navigate to its card.
   */
  onSelectClause?: (clauseId: string) => void;
}

export const ContractIssuesPanel: React.FC<ContractIssuesPanelProps> = ({
  issues,
  clauseLookup,
  onSelectClause,
}) => {
  if (!issues || issues.length === 0) {
    return null;
  }

  const getClauseLabel = (clauseId: string) => {
    const meta = clauseLookup?.get(clauseId);
    if (meta?.number) {
      return `clause ${meta.number}`;
    }
    return `clause ${clauseId}`;
  };

  const getClausePage = (clauseId: string, defaultPages: number[]) => {
    const meta = clauseLookup?.get(clauseId);
    if (meta?.pages && meta.pages.length > 0) {
      return `Page ${meta.pages[0]}`;
    }
    if (defaultPages && defaultPages.length > 0) {
      return `Page ${defaultPages[0]}`;
    }
    return "Page 1";
  };

  return (
    <section
      className="contract-issues-panel"
      aria-labelledby="contract-issues-title"
      data-testid="contract-issues-panel"
    >
      <header className="issues-panel-header">
        <div className="issues-title-row">
          <span className="issues-alert-icon" aria-hidden="true">⚠️</span>
          <div>
            <h2 id="contract-issues-title" className="issues-panel-title">
              Contract-Wide Issues ({issues.length})
            </h2>
            <p className="issues-panel-subtitle">
              These clauses contradict or override each other across pages. Check these carefully before signing.
            </p>
          </div>
        </div>
      </header>

      <div className="issues-list">
        {issues.map((issue, idx) => {
          const idA = issue.clause_ids[0];
          const idB = issue.clause_ids[1];
          const labelA = getClauseLabel(idA);
          const labelB = getClauseLabel(idB);
          const pageA = getClausePage(idA, issue.pages);
          const pageB = getClausePage(idB, issue.pages);
          const isConflict = issue.kind === "conflict";

          return (
            <article
              key={`${idA}-${idB}-${idx}`}
              className={`issue-item ${isConflict ? "issue-conflict" : "issue-override"}`}
              data-testid={`issue-item-${idx}`}
            >
              <div className="issue-item-meta">
                <span
                  className={`issue-kind-badge ${
                    isConflict ? "badge-conflict" : "badge-override"
                  }`}
                >
                  {isConflict ? "Contradiction / Conflict" : "Override Claim"}
                </span>

                <div className="issue-locations" data-testid="issue-locations">
                  <button
                    type="button"
                    onClick={() => onSelectClause?.(idA)}
                    className="clause-location-btn"
                    title={`Jump to ${labelA}`}
                    aria-label={`Jump to ${pageA}, ${labelA}`}
                  >
                    {pageA}, {labelA}
                  </button>
                  <span className="locations-separator"> and </span>
                  <button
                    type="button"
                    onClick={() => onSelectClause?.(idB)}
                    className="clause-location-btn"
                    title={`Jump to ${labelB}`}
                    aria-label={`Jump to ${pageB}, ${labelB}`}
                  >
                    {pageB}, {labelB}
                  </button>
                </div>
              </div>

              <p className="issue-explanation">{issue.explanation}</p>

              {issue.quotes && issue.quotes.length === 2 && (
                <details className="issue-quotes-wrapper">
                  <summary className="toggle-quotes-btn">
                    View exact contract wording
                  </summary>

                  <div className="issue-quotes-content" data-testid="issue-quotes-content">
                    <div className="quote-block">
                      <span className="quote-label">{labelA}:</span>
                      <blockquote className="quote-text">“{issue.quotes[0]}”</blockquote>
                    </div>
                    <div className="quote-block">
                      <span className="quote-label">{labelB}:</span>
                      <blockquote className="quote-text">“{issue.quotes[1]}”</blockquote>
                    </div>
                  </div>
                </details>
              )}

              <footer className="issue-impartial-note">
                Mbiu reports that one clause claims to override another; it never decides which a court would apply.
              </footer>
            </article>
          );
        })}
      </div>
    </section>
  );
};
