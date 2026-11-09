"use client";

import React from "react";

export const ReportGuide: React.FC = () => {
  return (
    <section className="report-section">
      <h2 className="report-section-heading">1. How to Read This Report</h2>
      <p className="report-text">
        Every analyzed clause is categorized using one of four objective evaluation labels.
        <strong> Typical does not mean safe.</strong> A clause may be common in the music
        industry and still contain restrictive terms. Mbiu uses no green labels.
      </p>

      <table className="report-table">
        <thead>
          <tr>
            <th style={{ width: "25%" }}>Label</th>
            <th>Meaning for the Artist</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>[TYPICAL]</strong></td>
            <td>
              Typical of reference contract standards in our system. Reference contracts
              commonly include a clause with the same practical effect.
            </td>
          </tr>
          <tr>
            <td><strong>[UNUSUAL]</strong></td>
            <td>
              Not typically present in reference contract standards, but we found no major or
              meaningful adverse effect on your money, music, time, or freedom.
            </td>
          </tr>
          <tr>
            <td><strong>[WORTH ASKING ABOUT]</strong></td>
            <td>
              Not typical of reference contract standards, and could affect your money, music,
              time, or freedom to take other work in a minor or major way.
            </td>
          </tr>
          <tr>
            <td><strong>[COULDN&apos;T COMPARE]</strong></td>
            <td>
              Insufficient reference standard templates on this topic, or comparison checks
              could not run safely. The plain-language explanation is still shown.
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
};
