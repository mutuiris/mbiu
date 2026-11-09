"use client";

import React from "react";

export interface MissingProtection {
  title: string;
  ask_them: string;
}

export interface ReportProtectionsProps {
  missingProtections?: MissingProtection[];
}

export const ReportProtections: React.FC<ReportProtectionsProps> = ({
  missingProtections,
}) => {
  if (!missingProtections || missingProtections.length === 0) return null;

  return (
    <section className="report-section">
      <h2 className="report-section-heading">5. Missing Protections (&ldquo;Not Found in Your Contract&rdquo;)</h2>
      <p className="report-text">
        Standard templates for this contract type commonly include the following protective terms,
        which were not found in your contract text.
      </p>

      <div className="report-checklist">
        {missingProtections.map((m, idx) => (
          <div key={idx} className="missing-protection-entry">
            <p>
              <strong>5.{idx + 1} {m.title}:</strong> {m.ask_them}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};
