"use client";

import React from "react";

export interface ResultsBarProps {
  onOpenReport: () => void;
}

export const ResultsBar: React.FC<ResultsBarProps> = ({ onOpenReport }) => {
  return (
    <div className="results-actions-bar">
      <button
        type="button"
        onClick={onOpenReport}
        className="download-report-btn"
        data-testid="download-report-btn"
        aria-label="Download evaluation report"
      >
        📄 Download Report
      </button>
    </div>
  );
};
