"use client";

import React from "react";
import type { ContractIssue } from "@/lib/api/generated/types.gen";

export interface IssueItemProps {
  issue: ContractIssue;
  index: number;
  clauseLookup?: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
  onSelectClause?: (clauseId: string) => void;
}

export const IssueItem: React.FC<IssueItemProps> = ({
  issue,
  index,
  clauseLookup,
  onSelectClause,
}) => {
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

  const idA = issue.clause_ids[0];
  const idB = issue.clause_ids[1];
  const labelA = getClauseLabel(idA);
  const labelB = getClauseLabel(idB);
  const pageA = getClausePage(idA, issue.pages);
  const pageB = getClausePage(idB, issue.pages);
  const isConflict = issue.kind === "conflict";

  return (
    <article
      className={`issue-item ${isConflict ? "issue-conflict" : "issue-override"}`}
      data-testid={`issue-item-${index}`}
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
};
