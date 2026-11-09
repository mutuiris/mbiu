"use client";

import React from "react";

export interface CalcTermsProps {
  royaltyRate: number;
  quotedRateText?: string | null;
  isNet: boolean;
  quotedBasisText?: string | null;
  deductionQuotes: string[];
}

export const CalcTerms: React.FC<CalcTermsProps> = ({
  royaltyRate,
  quotedRateText,
  isNet,
  quotedBasisText,
  deductionQuotes,
}) => {
  return (
    <div className="calc-terms-summary">
      <div className="term-item">
        <span className="term-name">Royalty rate:</span>
        <span className="term-value font-semibold">{royaltyRate}%</span>
        {quotedRateText && (
          <span className="term-quote" title="Exact wording in contract">
            (from “{quotedRateText}”)
          </span>
        )}
      </div>

      <div className="term-item">
        <span className="term-name">Basis:</span>
        <span className={`term-value basis-badge ${isNet ? "basis-net" : "basis-gross"}`}>
          {isNet ? "Net (Deductions taken first)" : "Gross (Calculated before deductions)"}
        </span>
        {quotedBasisText && (
          <span className="term-quote" title="Exact wording in contract">
            (from “{quotedBasisText}”)
          </span>
        )}
      </div>

      {deductionQuotes.length > 0 && (
        <div className="deductions-list-wrap">
          <span className="term-name">Deductions stated in contract:</span>
          <div className="deductions-tags">
            {deductionQuotes.map((quote, idx) => (
              <span key={idx} className="deduction-tag">
                “{quote}”
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
