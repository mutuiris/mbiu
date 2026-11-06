import React from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";

interface ClauseCardProps {
  result: ClauseResult;
  clauseNumber?: string | null;
  clauseHeading?: string | null;
  isHighlighted?: boolean;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({
  result,
  clauseNumber,
  clauseHeading,
  isHighlighted = false,
}) => {
  const getBadgeConfig = (comparison: ClauseResult["comparison"]) => {
    switch (comparison) {
      case "worse_for_you":
        return {
          label: "Worse than standard",
          className: "badge-worse",
        };
      case "better_for_you":
        return {
          label: "Better than standard",
          className: "badge-better",
        };
      case "not_in_standard":
        return {
          label: "Not in standard",
          className: "badge-notice",
        };
      case "missing_from_contract":
        return {
          label: "Missing from contract",
          className: "badge-warning",
        };
      case "cannot_compare":
        return {
          label: "Cannot compare",
          className: "badge-muted",
        };
      default:
        return {
          label: comparison.replace(/_/g, " "),
          className: "badge-neutral",
        };
    }
  };

  const badge = getBadgeConfig(result.comparison);
  const locationLabel = `Page ${result.pages.join(", ")}${
    clauseNumber ? ` · Clause ${clauseNumber}` : ""
  }${clauseHeading ? ` (${clauseHeading})` : ""}`;

  return (
    <article
      id={`card-${result.clause_id}`}
      className={`result-card ${badge.className} ${isHighlighted ? "highlighted" : ""}`}
      aria-labelledby={`headline-${result.clause_id}`}
    >
      <header className="card-header">
        <div className="card-meta">
          <span className={`status-badge ${badge.className}`}>{badge.label}</span>
          <span className="card-location">{locationLabel}</span>
        </div>
        <h3 id={`headline-${result.clause_id}`} className="card-headline">
          {result.headline}
        </h3>
      </header>

      <section className="card-comparison-section">
        <div className="comparison-row your-contract">
          <span className="comparison-label">Your contract:</span>
          <blockquote className="comparison-quote">
            “{result.what_it_says}”
          </blockquote>
        </div>

        {result.standard_excerpt && (
          <div className="comparison-row standard-practice">
            <span className="comparison-label">Reviewed standard:</span>
            <p className="comparison-text">{result.standard_excerpt}</p>
          </div>
        )}

        {result.fairer_wording && (
          <div className="comparison-row fairer-wording">
            <span className="comparison-label">Fairer wording:</span>
            <p className="fairer-text">{result.fairer_wording}</p>
          </div>
        )}

        <div className="card-meaning-box">
          <span className="meaning-title">What this means for you:</span>
          <p className="meaning-text">{result.what_it_means}</p>
        </div>
      </section>

      {result.ask_them && (
        <footer className="card-ask-them-section">
          <div className="ask-them-badge">Ask them:</div>
          <p className="ask-them-text">“{result.ask_them}”</p>
        </footer>
      )}
    </article>
  );
};
