"use client";

import React, { useEffect, useState } from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";
import { ShillingsCalculator } from "./ShillingsCalculator";

export interface LinkedClauseItem {
  clauseId: string;
  label: string;
  issueKind?: "conflict" | "override" | null;
}

export interface CopyButtonProps {
  text: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  label = "📋 Copy",
  copiedLabel = "✓ Copied!",
  className = "copy-btn",
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Clipboard fallback
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`${className} ${copied ? "copied" : ""}`}
      aria-label="Copy to clipboard"
    >
      {copied ? copiedLabel : label}
    </button>
  );
};

export interface ReadAloudButtonProps {
  text: string;
}

export const ReadAloudButton: React.FC<ReadAloudButtonProps> = ({ text }) => {
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeech = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-KE";
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <button
      type="button"
      onClick={handleToggleSpeech}
      className={`read-aloud-btn ${isSpeaking ? "speaking" : ""}`}
      aria-label={isSpeaking ? "Stop reading aloud" : "Read card summary aloud"}
      title={isSpeaking ? "Stop speech" : "Read aloud on this device"}
    >
      <span className="speaker-icon" aria-hidden="true">
        {isSpeaking ? "⏹" : "🔊"}
      </span>
      <span>{isSpeaking ? "Stop reading" : "Read aloud"}</span>
      {isSpeaking && <span className="speaking-pulse" aria-hidden="true"></span>}
    </button>
  );
};

export interface ClauseCardProps {
  result: ClauseResult;
  clauseNumber?: string | null;
  clauseHeading?: string | null;
  topic?: string | null;
  isHighlighted?: boolean;
  isUpdated?: boolean;
  linkedClauses?: LinkedClauseItem[];
  onSelectClause?: (clauseId: string) => void;
  onJumpToPdfClause?: (clauseId: string, pageNumber: number) => void;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({
  result,
  clauseNumber,
  clauseHeading,
  topic,
  isHighlighted = false,
  isUpdated = false,
  linkedClauses = [],
  onSelectClause,
  onJumpToPdfClause,
}) => {
  const BADGE_CLASS: Record<OutcomeTone, string> = {
    typical: "badge-typical",
    unusual: "badge-unusual",
    worth_asking_about: "badge-worth",
    cannot_compare: "badge-cannot-compare",
  };
  const getBadgeConfig = (comparison: ClauseResult["comparison"]) => {
    const { label, tone } = outcomeLabel(comparison);
    return { label, tone, className: BADGE_CLASS[tone] };
  };

  const badge = getBadgeConfig(result.comparison);
  const formattedClauseNumber = clauseNumber
    ? clauseNumber.trim().toLowerCase().startsWith("clause")
      ? clauseNumber.trim()
      : `Clause ${clauseNumber.trim()}`
    : null;
  const clauseNumberValue = formattedClauseNumber
    ? formattedClauseNumber.replace(/^clause\s+/i, "").trim()
    : null;
  const topicText = topic || clauseHeading || "Contract Term";
  const headingTitle = formattedClauseNumber
    ? `${formattedClauseNumber}, ${topicText}`
    : topicText;

  const firstPage = result.pages[0] ?? 1;
  const locationLabel = `Page ${result.pages.join(", ")}${
    clauseNumber ? `, clause ${clauseNumber}` : ""
  }`;

  let sourcesText: string | null = null;
  if (result.evidence && result.evidence.length > 0) {
    sourcesText = result.evidence
      .map((ev) => `[${ev.source_title}]`)
      .filter((val, idx, arr) => arr.indexOf(val) === idx)
      .join(" · ");
  } else if (result.standard_template_id) {
    sourcesText = `[${result.standard_template_id}]`;
  }

  const speechText = [
    `${headingTitle}. ${badge.label}.`,
    `Location: ${locationLabel}.`,
    `What your contract says: ${result.what_it_says}.`,
    `In plain language: ${result.headline}.`,
    `Why this may matter to you: ${result.what_it_means}.`,
    result.standard_excerpt ? `How it compares: ${result.standard_excerpt}.` : "",
    result.comparison_note ? `Note: ${result.comparison_note}.` : "",
    result.ask_them ? `Question you could ask: ${result.ask_them}.` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const whatsappShareUrl = result.ask_them
    ? `https://wa.me/?text=${encodeURIComponent(
        `Mbiu Contract Review question for clause ${clauseNumber ? clauseNumber : ""}:\n"${result.ask_them}"`,
      )}`
    : "";

  return (
    <article
      id={`card-${result.clause_id}`}
      className={`result-card ${badge.className} ${isHighlighted ? "highlighted" : ""} ${
        isUpdated ? "card-updated" : ""
      }`}
      aria-labelledby={`heading-${result.clause_id} outcome-${result.clause_id}`}
      data-testid={`card-${result.clause_id}`}
    >
      {/* Outcome signal: clause number and outcome at a glance */}
      <div className="card-status-band" data-testid="status-band">
        <span className="band-clause">
          {formattedClauseNumber ?? "Contract clause"}
        </span>
        <span className="band-outcome" id={`outcome-${result.clause_id}`}>
          <span className="outcome-dot" aria-hidden="true" />
          {badge.label}
        </span>
      </div>

      {/* Whole-contract update notice */}
      {isUpdated && (
        <div
          className="card-updated-notice"
          role="status"
          data-testid="clause-updated-notice"
        >
          <span className="updated-dot" aria-hidden="true">
            ●
          </span>
          <span>Result updated based on whole-contract check</span>
        </div>
      )}

      {/* 1. Heading: Clause number and plain-language topic title */}
      <header className="card-heading-container" data-testid="clause-header">
        <div className="card-heading-line">
          {clauseNumberValue && (
            <span
              className="clause-number-disc"
              data-testid="clause-number-disc"
              aria-hidden="true"
            >
              {clauseNumberValue}
            </span>
          )}
          <h3
            id={`heading-${result.clause_id}`}
            className="card-heading"
            data-testid="clause-heading"
          >
            <span className="card-heading-title">{topicText}</span>
          </h3>
        </div>

        <div className="card-location-row" data-testid="status-topic-location">
          <button
            type="button"
            onClick={() => onJumpToPdfClause?.(result.clause_id, firstPage)}
            className="jump-to-pdf-trigger"
            aria-label={`Jump to page ${firstPage} in PDF viewer`}
            title={`Click to jump to page ${firstPage} in PDF viewer`}
          >
            <span className="meta-location">
              {locationLabel}
              <span className="pdf-jump-icon" aria-hidden="true">
                {" "}↗
              </span>
            </span>
          </button>
        </div>
      </header>

      {/* 2. What your contract says: Exact quote from the contract */}
      <section className="card-section card-what-it-says" data-testid="what-it-says-section">
        <h4 className="card-section-title">What your contract says</h4>
        <blockquote className="card-contract-quote text-contract">“{result.what_it_says}”</blockquote>
      </section>

      {/* 3. In plain language: 1-2 short, jargon-free sentences */}
      <section className="card-section card-plain-language" data-testid="plain-language-section">
        <h4 className="card-section-title">In plain language</h4>
        <p className="card-plain-language-text" data-testid="clause-headline">{result.headline}</p>
      </section>

      {/* 4. Why this may matter to you: Practical consequences + KES worked example for money */}
      <section className="card-comparison-section" data-testid="why-it-matters-section">
        <h4 className="card-section-title">Why this may matter to you</h4>
        <p className="card-meaning-text">{result.what_it_means}</p>

        {/* Illustrative KES worked example for money clauses */}
        {result.impact_inputs && (
          <div className="card-shillings-section" data-testid="shillings-calculator">
            <ShillingsCalculator inputs={result.impact_inputs} />
          </div>
        )}

        {/* Linked clauses / overrides / conflicts */}
        {linkedClauses && linkedClauses.length > 0 && (
          <div className="card-affected-by" data-testid="also-affected-by">
            <span className="affected-label">Also affected by:</span>
            <div className="affected-links">
              {linkedClauses.map((link) => (
                <button
                  key={link.clauseId}
                  type="button"
                  onClick={() => onSelectClause?.(link.clauseId)}
                  className={`affected-link-btn ${
                    link.issueKind ? `kind-${link.issueKind}` : ""
                  }`}
                  aria-label={`Jump to ${link.label}`}
                  title={`Jump to ${link.label}`}
                >
                  {link.issueKind === "conflict" && (
                    <span className="kind-icon" aria-hidden="true">
                      ⚠️{" "}
                    </span>
                  )}
                  {link.issueKind === "override" && (
                    <span className="kind-icon" aria-hidden="true">
                      ⚡{" "}
                    </span>
                  )}
                  <span>{link.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* 5. How it compares: What standard templates usually do (or comparison note) */}
      <section className="card-section card-how-it-compares" data-testid="how-it-compares-section">
        <h4 className="card-section-title">How it compares</h4>
        {result.standard_excerpt && (
          <p className="card-standard-excerpt text-standard">{result.standard_excerpt}</p>
        )}
        {result.comparison_note && (
          <p className="card-comparison-note" data-testid="clause-comparison-note">
            {result.comparison_note}
          </p>
        )}
        {!result.standard_excerpt && !result.comparison_note && (
          <p className="card-comparison-note text-muted">
            Standard reference templates on this topic were not compared.
          </p>
        )}
      </section>

      {/* 6. Questions you could ask: 1 to 3 neutral, specific questions */}
      {result.ask_them && (
        <section className="card-section card-ask-them-section" data-testid="ask-them-section">
          <div className="ask-them-header">
            <h4 className="card-section-title">Questions you could ask</h4>
            <div className="ask-them-actions">
              <CopyButton
                text={result.ask_them}
                label="📋 Copy"
                copiedLabel="✓ Copied"
                className="action-btn copy-action-btn"
              />
              <a
                href={whatsappShareUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="action-btn whatsapp-action-btn"
                aria-label="Share question to WhatsApp"
              >
                <span className="whatsapp-icon" aria-hidden="true">
                  💬
                </span>
                <span>WhatsApp</span>
              </a>
            </div>
          </div>
          <p className="ask-them-text">“{result.ask_them}”</p>
        </section>
      )}

      {/* 7. Sources: Reference contract title and page when cited */}
      {sourcesText && (
        <section className="card-section card-sources-section" data-testid="sources-section">
          <div className="card-sources">
            <span className="sources-title">Sources: </span>
            <span className="sources-content">{sourcesText}</span>
          </div>
        </section>
      )}

      {/* 8. Notice: Standard disclaimer */}
      <div className="card-notice" data-testid="clause-notice">
        <p className="card-notice-disclaimer">
          <em>This explains what the contract says compared with reference material. It doesn’t say whether a clause is lawful or enforceable, and it isn’t legal advice.</em>
        </p>
      </div>

      {/* Collapsible raw clause inspection */}
      <section className="card-exact-wording-section" data-testid="exact-wording-section">
        <details className="exact-wording-details">
          <summary className="exact-wording-summary">
            <span className="summary-icon" aria-hidden="true">
              🔍
            </span>
            <span>Show exact wording</span>
            <span className="summary-hint">(original clause & template excerpt)</span>
          </summary>

          <div className="exact-wording-body">
            <div className="wording-block">
              <span className="wording-sublabel">Original contract clause (unaltered):</span>
              <blockquote className="exact-text-quote">{result.original_text}</blockquote>
            </div>

            {result.standard_excerpt && (
              <div className="wording-block">
                <span className="wording-sublabel">Reviewed template excerpt:</span>
                <blockquote className="exact-template-quote">
                  {result.standard_excerpt}
                </blockquote>
              </div>
            )}
          </div>
        </details>
      </section>

      {/* Read aloud with the browser's speech synthesis */}
      <footer className="card-read-aloud-footer" data-testid="read-aloud-section">
        <ReadAloudButton text={speechText} />
      </footer>
    </article>
  );
};
