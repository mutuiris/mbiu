"use client";

import React from "react";

export interface ReportDashboardProps {
  labelCounts: {
    typical: number;
    unusual: number;
    worth_asking_about: number;
    cannot_compare: number;
  };
  issuesCount: number;
  missingProtectionsCount: number;
  topAsks?: { question: string }[];
}

export const ReportDashboard: React.FC<ReportDashboardProps> = ({
  labelCounts,
  issuesCount,
  missingProtectionsCount,
  topAsks = [],
}) => {
  return (
    <section className="report-section">
      <h2 className="report-section-heading">2. Executive Summary Dashboard</h2>

      <table className="report-table summary-counts-table">
        <thead>
          <tr>
            <th>Typical</th>
            <th>Unusual</th>
            <th>Worth Asking About</th>
            <th>Couldn&apos;t Compare</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="count-cell">{labelCounts.typical}</td>
            <td className="count-cell">{labelCounts.unusual}</td>
            <td className="count-cell">{labelCounts.worth_asking_about}</td>
            <td className="count-cell">{labelCounts.cannot_compare}</td>
          </tr>
        </tbody>
      </table>

      <div className="report-meta-summary">
        <p><strong>Contract-wide contradictions or overrides:</strong> {issuesCount}</p>
        <p><strong>Missing standard protections (reverse check):</strong> {missingProtectionsCount}</p>
      </div>

      {topAsks && topAsks.length > 0 && (
        <div className="top-questions-block">
          <h3 className="report-subheading">Priority Questions to Ask Counterparty:</h3>
          <ol className="report-numbered-list">
            {topAsks.slice(0, 3).map((ask, i) => (
              <li key={i}>
                <strong>&ldquo;{ask.question}&rdquo;</strong>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
};
