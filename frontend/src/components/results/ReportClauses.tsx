"use client";

import React from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel } from "@/lib/outcome";

export interface ReportClausesProps {
  highImpactResults: ClauseResult[];
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
}

export const ReportClauses: React.FC<ReportClausesProps> = ({
  highImpactResults,
  clauseLookup,
}) => {
  return (
    <section className="report-section">
      <h2 className="report-section-heading">4. Breakdown of High-Impact Evaluated Clauses</h2>
      <p className="report-text">
        The following clauses represent the key terms governing royalties, ownership, duration,
        restrictions, and liability.
      </p>

      {highImpactResults.map((result, idx) => {
        const extra = clauseLookup.get(result.clause_id);
        const num = extra?.number ? `Clause ${extra.number}` : `Clause ${idx + 1}`;
        const topic = extra?.heading || "Contract Term";
        const { label } = outcomeLabel(result.comparison);
        const pages = result.pages.join(", ");

        return (
          <div key={result.clause_id} className="report-clause-item">
            <h3 className="report-clause-title">
              4.{idx + 1} {num}, {topic} &mdash; [{label.toUpperCase()}]
            </h3>
            <p className="report-clause-location">Location: Page {pages}</p>

            <div className="report-clause-field">
              <strong>What your contract says:</strong>
              <blockquote className="report-quote">&ldquo;{result.what_it_says}&rdquo;</blockquote>
            </div>

            <div className="report-clause-field">
              <strong>In plain language:</strong> {result.headline}
            </div>

            <div className="report-clause-field">
              <strong>Why this may matter to you:</strong> {result.what_it_means}
            </div>

            <div className="report-clause-field">
              <strong>How it compares:</strong> {result.comparison_note || result.standard_excerpt || "Standard templates on this topic were not compared."}
            </div>

            {result.ask_them && (
              <div className="report-clause-field">
                <strong>Questions you could ask:</strong> &ldquo;{result.ask_them}&rdquo;
              </div>
            )}

            {result.evidence && result.evidence.length > 0 && (
              <div className="report-clause-field report-sources">
                <strong>Sources:</strong> {result.evidence.map((e) => `[${e.source_title}]`).join(" · ")}
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
};
