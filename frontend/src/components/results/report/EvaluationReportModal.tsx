"use client";

import React, { useMemo } from "react";
import type {
  DocumentPayload,
  ClauseResult,
  Summary,
  ContractMapPayload,
} from "@/lib/api/generated/types.gen";
import { outcomeLabel } from "@/lib/outcome";
import { ReportToolbar } from "./ReportToolbar";
import { ReportCover } from "./ReportCover";
import { ReportGuide } from "./ReportGuide";
import { ReportDashboard } from "./ReportDashboard";
import { ReportIssues } from "./ReportIssues";
import { ReportClauses } from "./ReportClauses";
import { ReportProtections } from "./ReportProtections";
import { ReportChecklist } from "./ReportChecklist";
import { ReportStandards } from "./ReportStandards";

export interface EvaluationReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentPayload | null;
  allResults: ClauseResult[];
  highImpactResults: ClauseResult[];
  contractMap: ContractMapPayload | null;
  summary: Summary | null;
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
  isStreaming?: boolean;
}

export const EvaluationReportModal: React.FC<EvaluationReportModalProps> = ({
  isOpen,
  onClose,
  document,
  allResults,
  highImpactResults,
  contractMap,
  summary,
  clauseLookup,
  isStreaming = false,
}) => {
  const currentDate = new Date().toLocaleDateString("en-KE", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const totalClauses = document?.clauses.length ?? allResults.length;
  const pageCount = document?.page_count ?? 1;

  // Tally label counts across all evaluated clauses
  const labelCounts = useMemo(() => {
    let typical = 0;
    let unusual = 0;
    let worth_asking_about = 0;
    let cannot_compare = 0;

    for (const r of allResults) {
      const { tone } = outcomeLabel(r.comparison);
      if (tone === "typical") typical++;
      else if (tone === "unusual") unusual++;
      else if (tone === "worth_asking_about") worth_asking_about++;
      else cannot_compare++;
    }

    return { typical, unusual, worth_asking_about, cannot_compare };
  }, [allResults]);

  // Aggregate all unique questions from clauses and summary
  const allQuestions = useMemo(() => {
    const list: string[] = [];
    const seen = new Set<string>();

    if (summary?.top_asks) {
      for (const a of summary.top_asks) {
        if (a.question && !seen.has(a.question)) {
          seen.add(a.question);
          list.push(a.question);
        }
      }
    }

    for (const r of allResults) {
      if (r.ask_them && !seen.has(r.ask_them)) {
        seen.add(r.ask_them);
        list.push(r.ask_them);
      }
    }

    if (summary?.missing_protections) {
      for (const m of summary.missing_protections) {
        if (m.ask_them && !seen.has(m.ask_them)) {
          seen.add(m.ask_them);
          list.push(m.ask_them);
        }
      }
    }

    return list;
  }, [summary, allResults]);

  // Aggregate reference standards cited
  const citedStandards = useMemo(() => {
    const set = new Set<string>();
    for (const r of allResults) {
      if (r.evidence) {
        for (const ev of r.evidence) {
          if (ev.source_title) set.add(ev.source_title);
        }
      }
      if (r.standard_template_id) {
        set.add(r.standard_template_id);
      }
    }
    return Array.from(set);
  }, [allResults]);

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="report-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-modal-title"
      data-testid="report-modal"
    >
      {/* Non-printing Control Bar */}
      <ReportToolbar onPrint={handlePrint} onClose={onClose} />

      {/* Printable Document Container */}
      <div className="report-modal-scroll-area">
        <article className="mbiu-printable-report" data-testid="printable-report">
          {/* Section 1: Cover / Header */}
          <ReportCover
            currentDate={currentDate}
            pageCount={pageCount}
            totalClauses={totalClauses}
            isStreaming={isStreaming}
            evaluatedCount={allResults.length}
          />

          <hr className="report-divider" />

          {/* Section 2: How to Read This Report */}
          <ReportGuide />

          <hr className="report-divider" />

          {/* Section 3: Executive Summary Dashboard */}
          <ReportDashboard
            labelCounts={labelCounts}
            issuesCount={contractMap?.issues?.length ?? 0}
            missingProtectionsCount={summary?.missing_protections?.length ?? 0}
            topAsks={summary?.top_asks}
          />

          <hr className="report-divider" />

          {/* Section 4: Contract-Wide Issues */}
          <ReportIssues
            issues={contractMap?.issues}
            clauseLookup={clauseLookup}
          />

          {contractMap?.issues && contractMap.issues.length > 0 && (
            <hr className="report-divider" />
          )}

          {/* Section 5: Breakdown of High-Impact Clauses */}
          <ReportClauses
            highImpactResults={highImpactResults}
            clauseLookup={clauseLookup}
          />

          <hr className="report-divider" />

          {/* Section 6: Missing Protections (Reverse Check) */}
          <ReportProtections
            missingProtections={summary?.missing_protections}
          />

          {summary?.missing_protections && summary.missing_protections.length > 0 && (
            <hr className="report-divider" />
          )}

          {/* Section 7: Negotiation Checklist of Questions */}
          <ReportChecklist questions={allQuestions} />

          <hr className="report-divider" />

          {/* Section 8: Reference Standards Cited & Section 9: Running Footer */}
          <ReportStandards
            standards={citedStandards}
            currentDate={currentDate}
            model={summary?.versions.model}
            corpus={summary?.versions.corpus}
          />
        </article>
      </div>
    </div>
  );
};
