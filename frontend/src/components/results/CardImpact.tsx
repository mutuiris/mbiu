"use client";

import React from "react";
import type { ImpactInputs } from "@/lib/api/generated/types.gen";
import { ShillingsCalculator } from "./ShillingsCalculator";

export interface LinkedClauseItem {
  clauseId: string;
  label: string;
  issueKind?: "conflict" | "override" | null;
}

export interface CardImpactProps {
  whatItMeans: string;
  impactInputs?: ImpactInputs | null;
  linkedClauses?: LinkedClauseItem[];
  onSelectClause?: (clauseId: string) => void;
}

export const CardImpact: React.FC<CardImpactProps> = ({
  whatItMeans,
  impactInputs,
  linkedClauses = [],
  onSelectClause,
}) => {
  return (
    <section className="card-comparison-section" data-testid="why-it-matters-section">
      <h4 className="card-section-title">Why this may matter to you</h4>
      <p className="card-meaning-text">{whatItMeans}</p>

      {/* Illustrative KES worked example for money clauses */}
      {impactInputs && (
        <div className="card-shillings-section" data-testid="shillings-calculator">
          <ShillingsCalculator inputs={impactInputs} />
        </div>
      )}

      {/* Linked clauses / overrides / conflicts */}
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
                  <span className="kind-icon" aria-hidden="true">
                    ⚠️{" "}
                  </span>
                )}
                {link.issueKind === "override" && (
                  <span className="kind-icon" aria-hidden="true">
                    ⚡{" "}
                  </span>
                )}
                <span>{link.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
