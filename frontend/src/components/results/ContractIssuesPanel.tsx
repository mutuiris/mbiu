"use client";

import React from "react";
import type { ContractIssue } from "@/lib/api/generated/types.gen";
import { IssueItem } from "./IssueItem";

export interface ContractIssuesPanelProps {
  issues: ContractIssue[];
  clauseLookup?: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
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
        {issues.map((issue, idx) => (
          <IssueItem
            key={`${issue.clause_ids[0]}-${issue.clause_ids[1]}-${idx}`}
            issue={issue}
            index={idx}
            clauseLookup={clauseLookup}
            onSelectClause={onSelectClause}
          />
        ))}
      </div>
    </section>
  );
};
