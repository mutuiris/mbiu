"use client";

import React from "react";

export interface CardHeaderProps {
  clauseId: string;
  headingTitle: string;
  badge: {
    display: string;
    className: string;
  };
  topicText: string;
  locationLabel: string;
  firstPage: number;
  onJumpToPdfClause?: (clauseId: string, pageNumber: number) => void;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  clauseId,
  headingTitle,
  badge,
  topicText,
  locationLabel,
  firstPage,
  onJumpToPdfClause,
}) => {
  return (
    <header className="card-heading-container" data-testid="clause-header">
      <div className="card-heading-line">
        <h3
          id={`heading-${clauseId}`}
          className="card-heading"
          data-testid="clause-heading"
        >
          <span className="card-heading-title">{headingTitle}</span>
          <span className="heading-separator" aria-hidden="true">
            {" "}·{" "}
          </span>
          <span className={`status-badge-inline ${badge.className}`}>
            {badge.display}
          </span>
        </h3>
      </div>

      <div className="card-location-row" data-testid="status-topic-location">
        <button
          type="button"
          onClick={() => onJumpToPdfClause?.(clauseId, firstPage)}
          className="jump-to-pdf-trigger"
          aria-label={`Jump to page ${firstPage} in PDF viewer`}
          title={`Click to jump to page ${firstPage} in PDF viewer`}
        >
          <span className="meta-topic">{topicText}</span>
          <span className="meta-separator" aria-hidden="true">
            {" "}·{" "}
          </span>
          <span className="meta-location">
            {locationLabel}
            <span className="pdf-jump-icon" aria-hidden="true">
              {" "}↗
            </span>
          </span>
        </button>
      </div>
    </header>
  );
};
