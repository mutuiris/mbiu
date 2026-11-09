"use client";

import React from "react";

export interface ReportCoverProps {
  currentDate: string;
  pageCount: number;
  totalClauses: number;
  isStreaming: boolean;
  evaluatedCount: number;
}

export const ReportCover: React.FC<ReportCoverProps> = ({
  currentDate,
  pageCount,
  totalClauses,
  isStreaming,
  evaluatedCount,
}) => {
  return (
    <header className="report-cover-section">
      <h1 className="report-main-title">MBIU CONTRACT EVALUATION REPORT</h1>
      <p className="report-subtitle">
        Independent Objective Comparison with Standard Contract Templates
      </p>

      <div className="report-meta-grid">
        <div className="meta-entry">
          <strong>Evaluation Date:</strong> {currentDate}
        </div>
        <div className="meta-entry">
          <strong>Contract Scope:</strong> {pageCount} page{pageCount === 1 ? "" : "s"} · {totalClauses} total clauses
        </div>
        <div className="meta-entry">
          <strong>Analysis Status:</strong> {isStreaming ? `In Progress (${evaluatedCount} clauses evaluated)` : `Completed (${evaluatedCount} clauses evaluated)`}
        </div>
        <div className="meta-entry">
          <strong>Report ID:</strong> MBIU-{new Date().getFullYear()}-{evaluatedCount}C
        </div>
      </div>

      <div className="report-disclaimer-box">
        <p>
          <strong>IMPORTANT NOTICE:</strong> This report explains what the contract says
          compared with reviewed reference material. It does not judge whether any clause is
          lawful or enforceable, and it is not legal advice. Mbiu is an educational contract
          analysis tool designed to help artists understand practical implications for money,
          music, time, and freedom before negotiation.
        </p>
      </div>
    </header>
  );
};
