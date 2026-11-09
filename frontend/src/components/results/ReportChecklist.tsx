"use client";

import React from "react";

export interface ReportChecklistProps {
  questions: string[];
}

export const ReportChecklist: React.FC<ReportChecklistProps> = ({ questions }) => {
  return (
    <section className="report-section">
      <h2 className="report-section-heading">6. Numbered Negotiation Checklist</h2>
      <p className="report-text">
        Use this checklist during meetings with your manager, record label, brand partner, or lawyer.
        Check each box once discussed and use the lines to record agreed terms.
      </p>

      <div className="report-questions-checklist">
        {questions.map((q, idx) => (
          <div key={idx} className="checklist-item">
            <div className="checklist-box-line">
              <span className="checkbox-square">[ &nbsp; ]</span>
              <span className="checklist-question">
                <strong>{idx + 1}.</strong> &ldquo;{q}&rdquo;
              </span>
            </div>
            <div className="notes-writing-lines">
              <div className="note-line">
                Notes: __________________________________________________________________________________
              </div>
              <div className="note-line">
                Agreed: _________________________________________________ Date: _______________ Initials: _____
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
