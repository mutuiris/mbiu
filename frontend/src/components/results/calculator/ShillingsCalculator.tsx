"use client";

import React, { useState } from "react";
import type { ImpactInputs } from "@/lib/api/generated/types.gen";
import {
  calculateImpact,
  hasClearFormula,
  DEFAULT_EXAMPLE_GROSS,
  DEFAULT_EXAMPLE_DEDUCTIONS,
} from "@/lib/impact";
import { CalcInputs } from "./CalcInputs";
import { CalcTerms } from "./CalcTerms";
import { CalcBreakdown } from "./CalcBreakdown";

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
      <CalcInputs
        grossInput={grossInput}
        deductionsInput={deductionsInput}
        hasDeductions={hasDeductions}
        onGrossChange={handleGrossChange}
        onDeductionsChange={handleDeductionsChange}
      />

      {/* Quoted Terms & Contract Deductions */}
      <CalcTerms
        royaltyRate={calc.royaltyRate}
        quotedRateText={calc.quotedRateText}
        isNet={isNet}
        quotedBasisText={calc.quotedBasisText}
        deductionQuotes={calc.deductionQuotes}
      />

      {/* Results Breakdown */}
      <CalcBreakdown
        artistEarnings={calc.artistEarnings}
        isNet={isNet}
        earningsUnderGross={calc.earningsUnderGross}
        lossToDeductions={calc.lossToDeductions}
        onReset={handleReset}
      />
    </section>
  );
};
