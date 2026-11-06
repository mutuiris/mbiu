"use client";

import React from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";

export interface LinkedClauseItem {
  clauseId: string;
  label: string;
  issueKind?: "conflict" | "override" | null;
}

export interface ClauseCardProps {
  result: ClauseResult;
  clauseNumber?: string | null;
  clauseHeading?: string | null;
  isHighlighted?: boolean;
  isUpdated?: boolean;
  linkedClauses?: LinkedClauseItem[];
  onSelectClause?: (clauseId: string) => void;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({
  result,
  clauseNumber,
  clauseHeading,
  isHighlighted = false,
  isUpdated = false,
  linkedClauses = [],
  onSelectClause,
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
      className={`result-card ${badge.className} ${isHighlighted ? "highlighted" : ""} ${
        isUpdated ? "card-updated" : ""
      }`}
      aria-labelledby={`headline-${result.clause_id}`}
      data-testid={`card-${result.clause_id}`}
    >
      {isUpdated && (
        <div
          className="card-updated-notice"
          role="status"
          data-testid="clause-updated-notice"
        >
          <span className="updated-dot" aria-hidden="true">●</span>
          <span>Result updated based on whole-contract check</span>
        </div>
      )}

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

        {result.comparison_note && (
          <div className="card-comparison-note" data-testid="clause-comparison-note">
            <span className="note-icon" aria-hidden="true">ℹ️</span>
            <p className="note-text">{result.comparison_note}</p>
          </div>
        )}

        {linkedClauses && linkedClauses.length > 0 && (
          <div className="card-affected-by" data-testid="also-affected-by">
            <span className="affected-label">Also affected by:</span>
            <div className="affected-links">
              {linkedClauses.map((link) => (
                <button
                  key={link.clauseId}
                  type="button"
                  onClick={() => onSelectClause?.(link.clauseId)}
                  className={`affected-link-btn ${
                    link.issueKind ? `kind-${link.issueKind}` : ""
                  }`}
                  aria-label={`Jump to ${link.label}`}
                  title={`Jump to ${link.label}`}
                >
                  {link.issueKind === "conflict" && (
                    <span className="kind-icon" aria-hidden="true">⚠️ </span>
                  )}
                  {link.issueKind === "override" && (
                    <span className="kind-icon" aria-hidden="true">⚡ </span>
                  )}
                  <span>{link.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
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
