"use client";

import React from "react";
import { formatShillings } from "@/lib/impact";

export interface CalcBreakdownProps {
  artistEarnings: number;
  isNet: boolean;
  earningsUnderGross: number;
  lossToDeductions: number;
  onReset: () => void;
}

export const CalcBreakdown: React.FC<CalcBreakdownProps> = ({
  artistEarnings,
  isNet,
  earningsUnderGross,
  lossToDeductions,
  onReset,
}) => {
  return (
    <div className="calc-results-card">
      <div className="result-row primary-payout">
        <span className="payout-label">Your calculated earnings:</span>
        <span className="payout-amount" data-testid="artist-earnings">
          {formatShillings(artistEarnings)}
        </span>
      </div>

      {isNet && (
        <div className="net-comparison-block" data-testid="net-comparison">
          <div className="comparison-metric">
            <span className="metric-label">If calculated on Gross:</span>
            <span className="metric-val">{formatShillings(earningsUnderGross)}</span>
          </div>
          <div className="comparison-metric loss-warning">
            <span className="metric-label">Loss to deductions:</span>
            <span className="metric-val">−{formatShillings(lossToDeductions)}</span>
          </div>
        </div>
      )}

      <div className="calc-reset-row">
        <button
          type="button"
          onClick={onReset}
          className="calc-reset-btn"
          aria-label="Reset example figures to defaults"
        >
          Reset example figures
        </button>
      </div>
    </div>
  );
};
