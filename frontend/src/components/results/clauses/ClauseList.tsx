"use client";

import React from "react";
import type { DocumentPayload, ClauseResult, ClauseFailure } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";

const PILL_CLASS: Record<OutcomeTone, string> = {
  typical: "typical",
  unusual: "unusual",
  worth_asking_about: "worth",
  cannot_compare: "cannot-compare",
};

export interface ClauseListProps {
  document: DocumentPayload;
  resultsByClauseId: Map<string, ClauseResult>;
  failedByClauseId: Map<string, ClauseFailure>;
  selectedClauseId?: string | null;
  onSelectClause?: (clauseId: string) => void;
}

export const ClauseList: React.FC<ClauseListProps> = ({
  document,
  resultsByClauseId,
  failedByClauseId,
  selectedClauseId,
  onSelectClause,
}) => {
  const [isExpanded, setIsExpanded] = React.useState(true);

  return (
    <section className="clauses-overview-panel" aria-label="Contract Clauses Overview">
      <div className="overview-header" onClick={() => setIsExpanded(!isExpanded)} role="button" tabIndex={0}>
        <div>
          <h2 className="overview-title">
            Document Clauses ({document.clauses.length} across {document.page_count} pages)
          </h2>
          <p className="overview-subtitle">
            All extracted clauses being checked against reviewed standards.
          </p>
        </div>
        <button
          type="button"
          className="toggle-btn"
          aria-expanded={isExpanded}
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? "Hide overview" : "Show overview"}
        </button>
      </div>

      {isExpanded && (
        <div className="clauses-table-wrapper">
          <ul className="clauses-grid" role="list">
            {document.clauses.map((clause) => {
              const result = resultsByClauseId.get(clause.clause_id);
              const failure = failedByClauseId.get(clause.clause_id);

              let statusBadge = <span className="status-pill pending">Checking…</span>;
              if (result) {
                const { label, tone } = outcomeLabel(result.comparison);
                statusBadge = <span className={`status-pill ${PILL_CLASS[tone]}`}>{label}</span>;
              } else if (failure) {
                statusBadge = <span className="status-pill cannot-compare">Couldn&apos;t compare</span>;
              }

              const isSelected = selectedClauseId === clause.clause_id;

              return (
                <li
                  key={clause.clause_id}
                  className={`clause-list-item ${isSelected ? "selected" : ""}`}
                  onClick={() => onSelectClause?.(clause.clause_id)}
                >
                  <div className="clause-item-main">
                    <span className="clause-item-num">
                      {clause.number ? `Clause ${clause.number}` : "Clause"}
                    </span>
                    <span className="clause-item-heading">
                      {clause.heading || "Untitled clause"}
                    </span>
                    <span className="clause-item-pages">
                      p. {clause.pages.join(", ")}
                    </span>
                  </div>
                  <div className="clause-item-status">{statusBadge}</div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
};
