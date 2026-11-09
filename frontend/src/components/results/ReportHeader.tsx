"use client";

import { Download } from "lucide-react";
import React, { type ReactNode } from "react";

import type { OutcomeTone } from "@/lib/outcome";

import { Button, ReportCard, TONE_CLASS } from "./ui";

export interface ReportHeaderProps {
  documentTitle: string | null;
  pageCount: number | null;
  checked: number;
  total: number;
  isStreaming: boolean;
  counts: Record<OutcomeTone, number>;
  notChecked: number;
  onCheckRest?: () => void;
  onDownload: () => void;
  onCheckAnother: () => void;
  /** The keep-results switch, owned by the page. */
  keep: ReactNode;
  /** Text on the download button while a PDF is being made. */
  downloadLabel?: string;
}

const COUNT_ORDER: { tone: OutcomeTone; label: string }[] = [
  { tone: "worth_asking_about", label: "Worth inquiry" },
  { tone: "unusual", label: "Unusual" },
  { tone: "typical", label: "Typical" },
  { tone: "cannot_compare", label: "Couldn't compare" },
];

export function ReportHeader({
  documentTitle,
  pageCount,
  checked,
  total,
  isStreaming,
  counts,
  notChecked,
  onCheckRest,
  onDownload,
  onCheckAnother,
  keep,
  downloadLabel = "Download report (PDF)",
}: ReportHeaderProps) {
  const meta = [documentTitle, pageCount ? `${pageCount} ${pageCount === 1 ? "page" : "pages"}` : null]
    .filter(Boolean)
    .join(" · ");
  const progress = isStreaming
    ? `Checking… ${checked} of ${total}`
    : `Done. Checked the ${checked} most important ${checked === 1 ? "clause" : "clauses"}.`;
  const percent = total > 0 ? Math.min(100, Math.round((checked / total) * 100)) : 0;

  return (
    <ReportCard aria-labelledby="report-title">
      <div className="min-w-0">
        <h1
          id="report-title"
          className="font-serif text-[1.7rem] font-medium leading-tight tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2rem]"
        >
          Your contract report
        </h1>
        {meta && <p className="mt-1 break-words text-[0.9rem] text-mbiu-ink/65 dark:text-[#b9c1c5]">{meta}</p>}
      </div>
      <div className="mt-4 hidden flex-wrap gap-2 lg:flex">
        <Button variant="primary" onClick={onDownload}>
          <Download aria-hidden="true" className="h-4 w-4" />
          {downloadLabel}
        </Button>
        <Button onClick={onCheckAnother}>Check another contract</Button>
      </div>

      <div className="mt-5" role="status" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <p className="text-[0.95rem] font-medium text-mbiu-ink dark:text-[#F4EFE6]">{progress}</p>
          {!isStreaming && notChecked > 0 && onCheckRest && (
            <Button onClick={onCheckRest}>Check the other {notChecked}</Button>
          )}
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-black/[0.06] dark:bg-white/10" aria-hidden="true">
          <div
            className="h-full rounded-full bg-mbiu-indigo transition-[width] duration-300 dark:bg-mbiu-indigo-dark"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {COUNT_ORDER.map(({ tone, label }) => (
          <div key={tone} className={`rounded-2xl px-3.5 py-3 ${TONE_CLASS[tone]}`}>
            <dd className="font-serif text-[1.6rem] font-semibold leading-none">{counts[tone]}</dd>
            <dt className="mt-1.5 text-[0.8rem] font-bold">{label}</dt>
          </div>
        ))}
      </dl>

      <div className="mt-5 flex flex-wrap gap-2 lg:hidden">
        <Button onClick={onCheckAnother} className="flex-1">
          Check another contract
        </Button>
      </div>

      {keep && <div className="mt-4 border-t border-[#e9dec9] pt-4 dark:border-white/10">{keep}</div>}
    </ReportCard>
  );
}
