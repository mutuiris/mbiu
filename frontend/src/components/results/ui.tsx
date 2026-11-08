"use client";

import { Collapsible } from "@base-ui/react/collapsible";
import { ChevronDown } from "lucide-react";
import React, { useState, type ButtonHTMLAttributes, type ReactNode } from "react";

import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

/** The report's one button pair: solid indigo, or outlined. */
export function Button({
  variant = "outline",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "outline" }) {
  return (
    <button
      type={type}
      className={cx(
        "report-press inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-full px-5 text-[0.92rem] font-semibold disabled:opacity-60",
        variant === "primary"
          ? "bg-mbiu-indigo text-white hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
          : "bg-transparent text-mbiu-ink shadow-[inset_0_0_0_1px_rgba(22,26,38,0.18)] hover:bg-black/[0.03] dark:text-[#F4EFE6] dark:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.22)] dark:hover:bg-white/[0.06]",
        className,
      )}
      {...props}
    />
  );
}

export const TONE_CLASS: Record<OutcomeTone, string> = {
  typical: "bg-[#0f6867]/10 text-[#0f6867] dark:bg-[#5fc4c1]/15 dark:text-[#8fdad7]",
  unusual: "bg-[#7a5600]/10 text-[#7a5600] dark:bg-[#e2b55a]/15 dark:text-[#ecc77e]",
  worth_asking_about: "bg-[#9a3412]/10 text-[#9a3412] dark:bg-[#f08a63]/15 dark:text-[#f5a786]",
  cannot_compare: "bg-[#57534e]/10 text-[#57534e] dark:bg-white/10 dark:text-[#cfcac4]",
};

/** Outcome label with its colour. Never wraps onto two lines. */
export function OutcomePill({ comparison }: { comparison: ClauseResult["comparison"] }) {
  const { label, tone } = outcomeLabel(comparison);
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[0.75rem] font-bold",
        TONE_CLASS[tone],
      )}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

/** A section that folds open and shut. `forceOpen` opens it, e.g. when the artist jumps to a clause inside. */
export function Fold({
  summary,
  children,
  defaultOpen = false,
  forceOpen = false,
  className,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  forceOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen || forceOpen);
  const [lastForced, setLastForced] = useState(forceOpen);
  if (forceOpen !== lastForced) {
    setLastForced(forceOpen);
    if (forceOpen) setOpen(true);
  }
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className={className}>
      <Collapsible.Trigger className="report-fold-trigger group inline-flex min-h-11 items-center gap-1.5 text-left text-[0.9rem] font-semibold text-mbiu-indigo underline-offset-4 hover:underline dark:text-[#a9b0ff]">
        {summary}
        <ChevronDown
          aria-hidden="true"
          className="h-4 w-4 shrink-0 transition-transform duration-200 group-data-[panel-open]:rotate-180"
        />
      </Collapsible.Trigger>
      {/* hiddenUntilFound keeps the text findable with the browser's find-in-page */}
      <Collapsible.Panel hiddenUntilFound className="report-fold-panel">
        {children}
      </Collapsible.Panel>
    </Collapsible.Root>
  );
}

/** The report's one card style. */
export function ReportCard({
  as: Tag = "section",
  className,
  children,
  ...props
}: {
  as?: "section" | "article" | "div";
  className?: string;
  children: ReactNode;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag
      className={cx(
        "rounded-[20px] border border-[#e9dec9] bg-[#fffdf8] p-4 sm:p-6 dark:border-white/10 dark:bg-white/[0.04]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}
