"use client";

import React, { useState } from "react";
import type { ImpactInputs } from "@/lib/api/generated/types.gen";
import {
  calculateImpact,
  formatShillings,
  hasClearFormula,
  DEFAULT_EXAMPLE_GROSS,
  DEFAULT_EXAMPLE_DEDUCTIONS,
} from "@/lib/impact";

export interface ShillingsCalculatorProps {
  inputs: ImpactInputs | null | undefined;
}

export const ShillingsCalculator: React.FC<ShillingsCalculatorProps> = ({ inputs }) => {
  const deductionCount = inputs?.deductions?.length ?? 0;
  const [grossInput, setGrossInput] = useState<number>(DEFAULT_EXAMPLE_GROSS);
  const [deductionsInput, setDeductionsInput] = useState<number>(
    deductionCount > 0 ? DEFAULT_EXAMPLE_DEDUCTIONS : 0,
  );

  if (!hasClearFormula(inputs)) {
    return null;
  }

  const calc = calculateImpact(inputs, grossInput, deductionsInput);
  if (!calc) return null;

  const isNet = calc.basis === "net";
  const hasDeductions = calc.deductionQuotes.length > 0 || calc.totalDeductions > 0;

  const handleGrossChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setGrossInput(Number.isNaN(val) ? 0 : Math.max(0, val));
  };

  const handleDeductionsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setDeductionsInput(Number.isNaN(val) ? 0 : Math.max(0, val));
  };

  const handleReset = () => {
    setGrossInput(DEFAULT_EXAMPLE_GROSS);
    setDeductionsInput(deductionCount > 0 ? DEFAULT_EXAMPLE_DEDUCTIONS : 0);
  };

  return (
    <section
      className="shillings-calculator"
      aria-labelledby="shillings-calc-title"
      data-testid="shillings-calculator"
    >
      <div className="calc-header">
        <div className="calc-title-row">
          <span className="calc-icon" aria-hidden="true">
            💰
          </span>
          <h4 id="shillings-calc-title" className="calc-title">
            In Shillings (Worked Example)
          </h4>
        </div>
        <span className="example-badge" aria-label="Notice: Figures are illustrative examples">
          Example figures — adjust below
        </span>
      </div>

      <p className="calc-disclaimer">
        These figures are illustrative examples to show how the clause formula works in practice.
        You can edit the numbers to test different revenue scenarios.
      </p>

      {/* Interactive Controls */}
      <div className="calc-controls-grid">
        <div className="calc-field">
          <label htmlFor="example-revenue-input" className="calc-label">
            Example gross revenue (KES)
            <span className="label-tag">Example</span>
          </label>
          <input
            id="example-revenue-input"
            type="number"
            min="0"
            step="10000"
            value={grossInput}
            onChange={handleGrossChange}
            className="calc-input"
            aria-describedby="example-revenue-hint"
          />
          <span id="example-revenue-hint" className="field-hint">
            Current: {formatShillings(grossInput)}
          </span>
        </div>

        {hasDeductions && (
          <div className="calc-field">
            <label htmlFor="example-deductions-input" className="calc-label">
              Example deductions before royalties (KES)
              <span className="label-tag">Example</span>
            </label>
            <input
              id="example-deductions-input"
              type="number"
              min="0"
              step="5000"
              value={deductionsInput}
              onChange={handleDeductionsChange}
              className="calc-input"
              aria-describedby="example-deductions-hint"
            />
            <span id="example-deductions-hint" className="field-hint">
              Current: {formatShillings(deductionsInput)}
            </span>
          </div>
        )}
      </div>

      {/* Quoted Terms & Contract Deductions */}
      <div className="calc-terms-summary">
        <div className="term-item">
          <span className="term-name">Royalty rate:</span>
          <span className="term-value font-semibold">{calc.royaltyRate}%</span>
          {calc.quotedRateText && (
            <span className="term-quote" title="Exact wording in contract">
              (from “{calc.quotedRateText}”)
            </span>
          )}
        </div>

        <div className="term-item">
          <span className="term-name">Basis:</span>
          <span className={`term-value basis-badge ${isNet ? "basis-net" : "basis-gross"}`}>
            {isNet ? "Net (Deductions taken first)" : "Gross (Calculated before deductions)"}
          </span>
          {calc.quotedBasisText && (
            <span className="term-quote" title="Exact wording in contract">
              (from “{calc.quotedBasisText}”)
            </span>
          )}
        </div>

        {calc.deductionQuotes.length > 0 && (
          <div className="deductions-list-wrap">
            <span className="term-name">Deductions stated in contract:</span>
            <div className="deductions-tags">
              {calc.deductionQuotes.map((quote, idx) => (
                <span key={idx} className="deduction-tag">
                  “{quote}”
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Results Breakdown */}
      <div className="calc-results-card">
        <div className="result-row primary-payout">
          <span className="payout-label">Your calculated earnings:</span>
          <span className="payout-amount" data-testid="artist-earnings">
            {formatShillings(calc.artistEarnings)}
          </span>
        </div>

        {isNet && (
          <div className="net-comparison-block" data-testid="net-comparison">
            <div className="comparison-metric">
              <span className="metric-label">If calculated on Gross:</span>
              <span className="metric-val">{formatShillings(calc.earningsUnderGross)}</span>
            </div>
            <div className="comparison-metric loss-warning">
              <span className="metric-label">Loss to deductions:</span>
              <span className="metric-val">−{formatShillings(calc.lossToDeductions)}</span>
            </div>
          </div>
        )}

        <div className="calc-reset-row">
          <button
            type="button"
            onClick={handleReset}
            className="calc-reset-btn"
            aria-label="Reset example figures to defaults"
          >
            Reset example figures
          </button>
        </div>
      </div>
    </section>
  );
};
