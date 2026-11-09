"use client";

import React, { useEffect, useState } from "react";

import type { ImpactInputs } from "@/lib/api/generated/types.gen";
import { EXAMPLE_GROSS, formatShillings, shillingSteps } from "@/lib/impact";

export interface ShillingsCalculatorProps {
  inputs: ImpactInputs | null | undefined;
}

/** What the quoted deductions take from an example amount. Never invents a royalty rate. */
export const ShillingsCalculator: React.FC<ShillingsCalculatorProps> = ({ inputs }) => {
  const [gross, setGross] = useState(EXAMPLE_GROSS);
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    if (!changing) return;
    const timer = setTimeout(() => setChanging(false), 200);
    return () => clearTimeout(timer);
  }, [changing, gross]);

  const steps = shillingSteps(inputs, gross);
  if (!steps) return null;

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/[^0-9]/g, "");
    setGross(digits ? Math.min(Number(digits), 1_000_000_000_000) : 0);
    setChanging(true);
  };

  const num = `tabular-nums transition-[opacity,filter] duration-200 ${changing ? "opacity-50 blur-[2px]" : ""}`;

  return (
    <section
      className="mt-4 rounded-2xl bg-black/[0.035] p-4 dark:bg-white/[0.05]"
      aria-labelledby="shillings-title"
      data-testid="shillings-calculator"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h4 id="shillings-title" className="text-[0.92rem] font-bold text-mbiu-ink dark:text-[#F4EFE6]">
          What this means in shillings
        </h4>
        <span className="text-[0.78rem] text-mbiu-ink/60 dark:text-[#b9c1c5]">Example figures, change them</span>
      </div>

      <label className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[0.9rem] text-mbiu-ink dark:text-[#F4EFE6]">
        If the label receives
        <input
          type="text"
          inputMode="numeric"
          value={gross.toLocaleString("en-KE")}
          onChange={onChange}
          aria-label="Example amount the label receives, in shillings"
          className="min-h-11 w-40 rounded-xl border border-[#e9dec9] bg-white px-3 text-right font-semibold tabular-nums text-mbiu-ink dark:border-white/15 dark:bg-white/[0.06] dark:text-[#F4EFE6]"
        />
      </label>

      <dl className="mt-3 space-y-1.5 text-[0.9rem]">
        {steps.steps.map((step, i) => (
          <div key={`${step.label}-${i}`} className="flex items-start justify-between gap-3">
            <dt className="min-w-0 text-[#9a3412] dark:text-[#f5a786]">
              − {step.label}
              {step.percent != null && ` ${step.percent}%`}
              <span className="block break-words text-[0.75rem] text-mbiu-ink/55 dark:text-[#b9c1c5]">“{step.quote}”</span>
            </dt>
            <dd className={`shrink-0 text-right ${num} ${step.amount == null ? "text-mbiu-ink/55 dark:text-[#b9c1c5]" : "text-[#9a3412] dark:text-[#f5a786]"}`}>
              {step.amount == null ? "Amount not stated here" : formatShillings(step.amount)}
            </dd>
          </div>
        ))}
        <div className="flex items-start justify-between gap-3 border-t border-black/10 pt-2 dark:border-white/10">
          <dt className="text-mbiu-ink dark:text-[#F4EFE6]">
            {steps.baseIsCeiling ? "At most, the amount your royalty is worked out on" : "The amount your royalty is worked out on"}
            {steps.baseIsCeiling && (
              <span className="block text-[0.75rem] text-mbiu-ink/55 dark:text-[#b9c1c5]">
                It will be less, because one charge has no stated amount.
              </span>
            )}
          </dt>
          <dd className={`shrink-0 font-semibold text-mbiu-ink dark:text-[#F4EFE6] ${num}`}>{formatShillings(steps.base)}</dd>
        </div>
        {steps.youReceive != null && steps.ratePercent != null && (
          <div className="flex items-start justify-between gap-3 text-[0.98rem] font-bold text-mbiu-ink dark:text-[#F4EFE6]">
            <dt>
              {steps.baseIsCeiling ? "At most, you receive" : "You receive"} at the contract&apos;s {steps.ratePercent}% royalty
            </dt>
            <dd className={`shrink-0 ${num}`}>{formatShillings(steps.youReceive)}</dd>
          </div>
        )}
      </dl>
    </section>
  );
};
