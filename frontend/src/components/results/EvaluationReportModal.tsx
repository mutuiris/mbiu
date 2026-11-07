"use client";

import React, { useMemo } from "react";
import type {
  DocumentPayload,
  ClauseResult,
  Summary,
  ContractMapPayload,
} from "@/lib/api/generated/types.gen";
import { outcomeLabel } from "@/lib/outcome";

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
      <div className="report-modal-toolbar no-print">
        <div className="toolbar-info">
          <span className="toolbar-title" id="report-modal-title">
            Evaluation Report Preview
          </span>
          <span className="toolbar-hint">
            Formatted in strict Black & White, Times New Roman 12pt for print & PDF export.
          </span>
        </div>
        <div className="toolbar-actions">
          <button
            type="button"
            onClick={handlePrint}
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

      {/* Printable Document Container */}
      <div className="report-modal-scroll-area">
        <article className="mbiu-printable-report" data-testid="printable-report">
          {/* Section 1: Cover / Header */}
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
                <strong>Analysis Status:</strong> {isStreaming ? `In Progress (${allResults.length} clauses evaluated)` : `Completed (${allResults.length} clauses evaluated)`}
              </div>
              <div className="meta-entry">
                <strong>Report ID:</strong> MBIU-{new Date().getFullYear()}-{allResults.length}C
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

          <hr className="report-divider" />

          {/* Section 2: How to Read This Report */}
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

          <hr className="report-divider" />

          {/* Section 3: Executive Summary Dashboard */}
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
              <p><strong>Contract-wide contradictions or overrides:</strong> {contractMap?.issues?.length ?? 0}</p>
              <p><strong>Missing standard protections (reverse check):</strong> {summary?.missing_protections?.length ?? 0}</p>
            </div>

            {summary?.top_asks && summary.top_asks.length > 0 && (
              <div className="top-questions-block">
                <h3 className="report-subheading">Priority Questions to Ask Counterparty:</h3>
                <ol className="report-numbered-list">
                  {summary.top_asks.slice(0, 3).map((ask, i) => (
                    <li key={i}>
                      <strong>&ldquo;{ask.question}&rdquo;</strong>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>

          <hr className="report-divider" />

          {/* Section 4: Contract-Wide Issues */}
          {contractMap?.issues && contractMap.issues.length > 0 && (
            <section className="report-section">
              <h2 className="report-section-heading">3. Contract-Wide Issues (Overrides &amp; Conflicts)</h2>
              <p className="report-text">
                These clauses pull in different directions across pages or explicitly claim to override
                other terms. Mbiu reports what each clause says; it does not decide which clause a court
                would apply.
              </p>

              {contractMap.issues.map((issue, idx) => {
                const c1 = clauseLookup.get(issue.clause_ids[0]);
                const c2 = clauseLookup.get(issue.clause_ids[1]);
                const loc1 = c1 ? `Page ${c1.pages?.join(", ") ?? "?"}${c1.number ? `, clause ${c1.number}` : ""}` : issue.clause_ids[0];
                const loc2 = c2 ? `Page ${c2.pages?.join(", ") ?? "?"}${c2.number ? `, clause ${c2.number}` : ""}` : issue.clause_ids[1];

                return (
                  <div key={idx} className="report-issue-card">
                    <p>
                      <strong>Issue {idx + 1} [{issue.kind.toUpperCase()}]:</strong> {issue.explanation}
                    </p>
                    <p className="report-indent-text">
                      <strong>Clauses involved:</strong> {loc1} and {loc2}
                    </p>
                    {issue.quotes && issue.quotes.length >= 2 && (
                      <p className="report-indent-text">
                        <strong>Quotes:</strong> &ldquo;{issue.quotes[0]}&rdquo; vs &ldquo;{issue.quotes[1]}&rdquo;
                      </p>
                    )}
                  </div>
                );
              })}
            </section>
          )}

          <hr className="report-divider" />

          {/* Section 5: Breakdown of High-Impact Clauses */}
          <section className="report-section">
            <h2 className="report-section-heading">4. Breakdown of High-Impact Evaluated Clauses</h2>
            <p className="report-text">
              The following clauses represent the key terms governing royalties, ownership, duration,
              restrictions, and liability.
            </p>

            {highImpactResults.map((result, idx) => {
              const extra = clauseLookup.get(result.clause_id);
              const num = extra?.number ? `Clause ${extra.number}` : `Clause ${idx + 1}`;
              const topic = extra?.heading || "Contract Term";
              const { label } = outcomeLabel(result.comparison);
              const pages = result.pages.join(", ");

              return (
                <div key={result.clause_id} className="report-clause-item">
                  <h3 className="report-clause-title">
                    4.{idx + 1} {num}, {topic} &mdash; [{label.toUpperCase()}]
                  </h3>
                  <p className="report-clause-location">Location: Page {pages}</p>

                  <div className="report-clause-field">
                    <strong>What your contract says:</strong>
                    <blockquote className="report-quote">&ldquo;{result.what_it_says}&rdquo;</blockquote>
                  </div>

                  <div className="report-clause-field">
                    <strong>In plain language:</strong> {result.headline}
                  </div>

                  <div className="report-clause-field">
                    <strong>Why this may matter to you:</strong> {result.what_it_means}
                  </div>

                  <div className="report-clause-field">
                    <strong>How it compares:</strong> {result.comparison_note || result.standard_excerpt || "Standard templates on this topic were not compared."}
                  </div>

                  {result.ask_them && (
                    <div className="report-clause-field">
                      <strong>Questions you could ask:</strong> &ldquo;{result.ask_them}&rdquo;
                    </div>
                  )}

                  {result.evidence && result.evidence.length > 0 && (
                    <div className="report-clause-field report-sources">
                      <strong>Sources:</strong> {result.evidence.map((e) => `[${e.source_title}]`).join(" · ")}
                    </div>
                  )}
                </div>
              );
            })}
          </section>

          <hr className="report-divider" />

          {/* Section 6: Missing Protections (Reverse Check) */}
          {summary?.missing_protections && summary.missing_protections.length > 0 && (
            <section className="report-section">
              <h2 className="report-section-heading">5. Missing Protections (&ldquo;Not Found in Your Contract&rdquo;)</h2>
              <p className="report-text">
                Standard templates for this contract type commonly include the following protective terms,
                which were not found in your contract text.
              </p>

              <div className="report-checklist">
                {summary.missing_protections.map((m, idx) => (
                  <div key={idx} className="missing-protection-entry">
                    <p>
                      <strong>5.{idx + 1} {m.title}:</strong> {m.ask_them}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <hr className="report-divider" />

          {/* Section 7: Negotiation Checklist of Questions */}
          <section className="report-section">
            <h2 className="report-section-heading">6. Numbered Negotiation Checklist</h2>
            <p className="report-text">
              Use this checklist during meetings with your manager, record label, brand partner, or lawyer.
              Check each box once discussed and use the lines to record agreed terms.
            </p>

            <div className="report-questions-checklist">
              {allQuestions.map((q, idx) => (
                <div key={idx} className="checklist-item">
                  <div className="checklist-box-line">
                    <span className="checkbox-square">[ &nbsp; ]</span>
                    <span className="checklist-question">
                      <strong>{idx + 1}.</strong> &ldquo;{q}&rdquo;
                    </span>
                  </div>
                  <div className="notes-writing-lines">
                    <div className="note-line">Notes: __________________________________________________________________________________</div>
                    <div className="note-line">Agreed: _________________________________________________ Date: _______________ Initials: _____</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <hr className="report-divider" />

          {/* Section 8: Reference Standards Cited */}
          {citedStandards.length > 0 && (
            <section className="report-section">
              <h2 className="report-section-heading">7. Reference Standards Cited</h2>
              <p className="report-text">
                Excerpts and comparison norms cited in this evaluation were sourced from the following reviewed public standards:
              </p>
              <ul className="report-bullet-list">
                {citedStandards.map((std, i) => (
                  <li key={i}>{std}</li>
                ))}
              </ul>
            </section>
          )}

          {/* Section 9: Running Footer */}
          <footer className="report-footer-section">
            <p className="footer-notice">
              Mbiu Contract Evaluation Report &bull; Not Legal Advice &bull; Independent Educational Evaluation
            </p>
            <p className="footer-versions">
              Generated: {currentDate} &bull; Model: {summary?.versions.model || "Gemini"} &bull; Corpus: {summary?.versions.corpus || "KECOBO/Indie-Standard"}
            </p>
          </footer>
        </article>
      </div>
    </div>
  );
};
