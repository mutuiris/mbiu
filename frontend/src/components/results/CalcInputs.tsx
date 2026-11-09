"use client";

import React from "react";
import { formatShillings } from "@/lib/impact";

export interface CalcInputsProps {
  grossInput: number;
  deductionsInput: number;
  hasDeductions: boolean;
  onGrossChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDeductionsChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const CalcInputs: React.FC<CalcInputsProps> = ({
  grossInput,
  deductionsInput,
  hasDeductions,
  onGrossChange,
  onDeductionsChange,
}) => {
  return (
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
          onChange={onGrossChange}
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
            onChange={onDeductionsChange}
            className="calc-input"
            aria-describedby="example-deductions-hint"
          />
          <span id="example-deductions-hint" className="field-hint">
            Current: {formatShillings(deductionsInput)}
          </span>
        </div>
      )}
    </div>
  );
};
