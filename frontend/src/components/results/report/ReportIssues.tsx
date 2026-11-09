"use client";

import React from "react";
import type { ContractIssue } from "@/lib/api/generated/types.gen";

export interface ReportIssuesProps {
  issues?: ContractIssue[];
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
}

export const ReportIssues: React.FC<ReportIssuesProps> = ({
  issues,
  clauseLookup,
}) => {
  if (!issues || issues.length === 0) return null;

  return (
    <section className="report-section">
      <h2 className="report-section-heading">3. Contract-Wide Issues (Overrides &amp; Conflicts)</h2>
      <p className="report-text">
        These clauses pull in different directions across pages or explicitly claim to override
        other terms. Mbiu reports what each clause says; it does not decide which clause a court
        would apply.
      </p>

      {issues.map((issue, idx) => {
        const c1 = clauseLookup.get(issue.clause_ids[0]);
        const c2 = clauseLookup.get(issue.clause_ids[1]);
        const loc1 = c1 ? `Page ${c1.pages?.join(", ") ?? "?"}${c1.number ? `, clause ${c1.number}` : ""}` : issue.clause_ids[0];
        const loc2 = c2 ? `Page ${c2.pages?.join(", ") ?? "?"}${c2.number ? `, clause ${c2.number}` : ""}` : issue.clause_ids[1];

        return (
          <div key={idx} className="report-issue-card">
            <p>
              <strong>Issue {idx + 1} [{issue.kind.toUpperCase()}]:</strong> {issue.explanation}
            </p>
            <p className="report-indent-text">
              <strong>Clauses involved:</strong> {loc1} and {loc2}
            </p>
            {issue.quotes && issue.quotes.length >= 2 && (
              <p className="report-indent-text">
                <strong>Quotes:</strong> &ldquo;{issue.quotes[0]}&rdquo; vs &ldquo;{issue.quotes[1]}&rdquo;
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
};
