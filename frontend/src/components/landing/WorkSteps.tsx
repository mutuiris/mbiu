import React from "react";

export interface StepItem {
  number: string;
  title: string;
  body: string;
}

const DEFAULT_STEPS: StepItem[] = [
  { number: "01", title: "Upload", body: "your contract." },
  { number: "02", title: "Understand", body: "each clause." },
  { number: "03", title: "Take your questions", body: "to the table." },
];

export interface WorkStepsProps {
  steps?: StepItem[];
  className?: string;
}

export function WorkSteps({ steps = DEFAULT_STEPS, className = "" }: WorkStepsProps) {
  return (
    <div className={`w-full ${className}`}>
      <div className="mx-auto flex max-w-[1120px] items-center gap-3 sm:gap-8">
        <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
        <h2 className="whitespace-nowrap font-serif text-[1.5rem] font-semibold italic tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.1rem]">
          How it works
        </h2>
        <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
      </div>

      <ol className="mx-auto mt-8 grid max-w-[980px] gap-6 sm:mt-10 sm:grid-cols-3 sm:gap-0">
        {steps.map((step, index) => (
          <li
            key={step.number}
            className={`flex items-center gap-4 sm:px-6 md:px-7 ${
              index > 0 ? "sm:border-l sm:border-mbiu-ink/20 dark:sm:border-white/15" : ""
            }`}
          >
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-mbiu-peach-strong text-[1.05rem] font-semibold text-[#1b2430] sm:h-14 sm:w-14 sm:text-[1.15rem]">
              {step.number}
            </span>
            <div>
              <p className="text-[0.98rem] font-semibold leading-tight text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.02rem]">
                {step.title}
              </p>
              <p className="text-[0.98rem] leading-tight text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.02rem]">
                {step.body}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
