import React from "react";
import type { ClauseFailure } from "@/lib/api/generated/types.gen";

interface ClauseFailedCardProps {
  failure: ClauseFailure;
  clauseNumber?: string | null;
  clauseHeading?: string | null;
  onRetry?: (clauseId: string) => void;
  isRetrying?: boolean;
}

export const ClauseFailedCard: React.FC<ClauseFailedCardProps> = ({
  failure,
  clauseNumber,
  clauseHeading,
  onRetry,
  isRetrying = false,
}) => {
  const clauseLabel = `${clauseNumber ? `Clause ${clauseNumber}` : "Clause"}${
    clauseHeading ? ` (${clauseHeading})` : ""
  }`;

  return (
    <article
      className="clause-failed-card"
      role="alert"
      aria-labelledby={`failed-title-${failure.clause_id}`}
    >
      <div className="failed-card-icon" aria-hidden="true">
        ⚠️
      </div>
      <div className="failed-card-content">
        <h4 id={`failed-title-${failure.clause_id}`} className="failed-card-title">
          {clauseLabel}
        </h4>
        <p className="failed-card-message">
          We couldn&apos;t check this clause just now. Your other results are below.
        </p>
        <span className="failed-card-reason">
          Reason: {failure.reason.replace(/_/g, " ")}
        </span>
      </div>
      {failure.retryable && onRetry && (
        <div className="failed-card-action">
          <button
            type="button"
            className="retry-btn"
            disabled={isRetrying}
            onClick={() => onRetry(failure.clause_id)}
          >
            {isRetrying ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}
    </article>
  );
};
