"use client";

import React from "react";

export interface ReportStandardsProps {
  standards: string[];
  currentDate: string;
  model?: string;
  corpus?: string;
}

export const ReportStandards: React.FC<ReportStandardsProps> = ({
  standards,
  currentDate,
  model = "Gemini",
  corpus = "KECOBO/Indie-Standard",
}) => {
  return (
    <>
      {standards.length > 0 && (
        <section className="report-section">
          <h2 className="report-section-heading">7. Reference Standards Cited</h2>
          <p className="report-text">
            Excerpts and comparison norms cited in this evaluation were sourced from the following reviewed public standards:
          </p>
          <ul className="report-bullet-list">
            {standards.map((std, i) => (
              <li key={i}>{std}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Running Footer */}
      <footer className="report-footer-section">
        <p className="footer-notice">
          Mbiu Contract Evaluation Report &bull; Not Legal Advice &bull; Independent Educational Evaluation
        </p>
        <p className="footer-versions">
          Generated: {currentDate} &bull; Model: {model} &bull; Corpus: {corpus}
        </p>
      </footer>
    </>
  );
};
