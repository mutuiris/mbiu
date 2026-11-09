"use client";

import React from "react";

export interface ReportToolbarProps {
  onPrint: () => void;
  onClose: () => void;
}

export const ReportToolbar: React.FC<ReportToolbarProps> = ({ onPrint, onClose }) => {
  return (
    <div className="report-modal-toolbar no-print">
      <div className="toolbar-info">
        <span className="toolbar-title" id="report-modal-title">
          Evaluation Report Preview
        </span>
        <span className="toolbar-hint">
          Formatted in strict Black &amp; White, Times New Roman 12pt for print &amp; PDF export.
        </span>
      </div>
      <div className="toolbar-actions">
        <button
          type="button"
          onClick={onPrint}
          className="report-action-btn primary"
          data-testid="print-report-btn"
        >
          🖨️ Print / Save as PDF
        </button>
        <button
          type="button"
          onClick={onClose}
          className="report-action-btn secondary"
          data-testid="close-report-btn"
        >
          ✕ Close
        </button>
      </div>
    </div>
  );
};
