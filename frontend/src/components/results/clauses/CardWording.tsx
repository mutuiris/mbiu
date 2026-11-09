"use client";

import React from "react";

export interface CardWordingProps {
  originalText: string;
  standardExcerpt?: string | null;
}

export const CardWording: React.FC<CardWordingProps> = ({
  originalText,
  standardExcerpt,
}) => {
  return (
    <section className="card-exact-wording-section" data-testid="exact-wording-section">
      <details className="exact-wording-details">
        <summary className="exact-wording-summary">
          <span className="summary-icon" aria-hidden="true">
            🔍
          </span>
          <span>Show exact wording</span>
          <span className="summary-hint">(original clause & template excerpt)</span>
        </summary>

        <div className="exact-wording-body">
          <div className="wording-block">
            <span className="wording-sublabel">Original contract clause (unaltered):</span>
            <blockquote className="exact-text-quote">{originalText}</blockquote>
          </div>

          {standardExcerpt && (
            <div className="wording-block">
              <span className="wording-sublabel">Reviewed template excerpt:</span>
              <blockquote className="exact-template-quote">
                {standardExcerpt}
              </blockquote>
            </div>
          )}
        </div>
      </details>
    </section>
  );
};
