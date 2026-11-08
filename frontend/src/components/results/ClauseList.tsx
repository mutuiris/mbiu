import React from "react";
import type { DocumentPayload, ClauseResult, ClauseFailure } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";

const PILL_CLASS: Record<OutcomeTone, string> = {
  typical: "typical",
  unusual: "unusual",
  worth_asking_about: "worth",
  cannot_compare: "cannot-compare",
};

interface ClauseListProps {
  document: DocumentPayload;
  resultsByClauseId: Map<string, ClauseResult>;
  failedByClauseId: Map<string, ClauseFailure>;
  selectedClauseId?: string | null;
  onSelectClause?: (clauseId: string) => void;
  isStreaming?: boolean;
}

export const ClauseList: React.FC<ClauseListProps> = ({
  document,
  resultsByClauseId,
  failedByClauseId,
  selectedClauseId,
  onSelectClause,
  isStreaming = false,
}) => {
  // During active streaming, keep the overview open by default so the user sees clauses
  // being labeled live. Once done, collapse it by default unless manually toggled.
  const [userToggled, setUserToggled] = React.useState<boolean | null>(null);
  const isExpanded = userToggled !== null ? userToggled : isStreaming;

  const evaluatedCount = resultsByClauseId.size;
  const totalCount = document.clauses.length;

  return (
    <section className="clauses-overview-panel" aria-label="Contract Clauses Overview">
      <div
        className="overview-header"
        onClick={() => setUserToggled(!isExpanded)}
        role="button"
        tabIndex={0}
      >
        <div>
          <h2 className="overview-title">
            Document Clauses ({evaluatedCount} of {totalCount} evaluated)
          </h2>
          <p className="overview-subtitle">
            {isStreaming
              ? "Checking and labeling clauses live against reviewed standards…"
              : "All extracted clauses evaluated against reviewed standards."}
          </p>
        </div>
        <button
          type="button"
          className="toggle-btn"
          aria-expanded={isExpanded}
          onClick={(e) => {
            e.stopPropagation();
            setUserToggled(!isExpanded);
          }}
        >
          {isExpanded ? "Hide overview" : "View all clauses"}
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
