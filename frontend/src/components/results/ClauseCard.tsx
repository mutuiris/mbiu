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
    typical: "badge-better",
    unusual: "badge-notice",
    inquiry: "badge-worse",
    unchecked: "badge-muted",
  };
  const getBadgeConfig = (comparison: ClauseResult["comparison"]) => {
    const { label, tone } = outcomeLabel(comparison);
    return { label, className: BADGE_CLASS[tone] };
  };

  const badge = getBadgeConfig(result.comparison);
  const topicText = topic || clauseHeading || "Contract Term";
  const firstPage = result.pages[0] ?? 1;
  const locationLabel = `Page ${result.pages.join(", ")}${
    clauseNumber ? `, clause ${clauseNumber}` : ""
  }`;

  const speechText = [
    result.headline,
    `Status: ${badge.label}.`,
    `Topic: ${topicText}.`,
    `Location: ${locationLabel}.`,
    `Your contract says: ${result.what_it_says}.`,
    result.standard_excerpt ? `Reviewed standard says: ${result.standard_excerpt}.` : "",
    `What this means for you: ${result.what_it_means}.`,
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
      aria-labelledby={`headline-${result.clause_id}`}
      data-testid={`card-${result.clause_id}`}
    >
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

      {/* 1. Headline in artist's terms */}
      <div className="card-headline-wrapper">
        <h3
          id={`headline-${result.clause_id}`}
          className="card-headline"
          data-testid="clause-headline"
        >
          {result.headline}
        </h3>
      </div>

      {/* 2. Status, topic and location (tapping jumps to the clause in the PDF viewer) */}
      <div className="card-status-topic-location" data-testid="status-topic-location">
        <button
          type="button"
          onClick={() => onJumpToPdfClause?.(result.clause_id, firstPage)}
          className="jump-to-pdf-trigger"
          aria-label={`Jump to page ${firstPage} in PDF viewer`}
          title={`Click to jump to page ${firstPage} in PDF viewer`}
        >
          <span className={`status-badge-inline ${badge.className}`}>{badge.label}</span>
          <span className="meta-separator" aria-hidden="true">
            ·
          </span>
          <span className="meta-topic">{topicText}</span>
          <span className="meta-separator" aria-hidden="true">
            ·
          </span>
          <span className="meta-location">
            {locationLabel}
            <span className="pdf-jump-icon" aria-hidden="true">
              {" "}
              ↗
            </span>
          </span>
        </button>
      </div>

      {/* 3, 4, 5 Comparison Section */}
      <section className="card-comparison-section" data-testid="contract-vs-standard">
        {/* 3. Your contract vs the standard, one line each */}
        <div className="comparison-line your-contract-line">
          <span className="line-label">Your contract:</span>
          <p className="line-content text-contract">“{result.what_it_says}”</p>
        </div>

        {result.standard_excerpt && (
          <div className="comparison-line standard-line">
            <span className="line-label">The standard:</span>
            <p className="line-content text-standard">{result.standard_excerpt}</p>
          </div>
        )}

        <div className="card-meaning-box">
          <span className="meaning-title">What this means for you:</span>
          <p className="meaning-text">{result.what_it_means}</p>
        </div>

        {result.comparison_note && (
          <div className="card-comparison-note" data-testid="clause-comparison-note">
            <span className="note-icon" aria-hidden="true">
              ℹ️
            </span>
            <p className="note-text">{result.comparison_note}</p>
          </div>
        )}

        {/* 4. In shillings: worked example from impact_inputs */}
        {result.impact_inputs && (
          <div className="card-shillings-section">
            <ShillingsCalculator inputs={result.impact_inputs} />
          </div>
        )}

        {/* 5. Also affected by */}
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

      {/* Ask them, with Copy and Share to WhatsApp */}
      {result.ask_them && (
        <section className="card-ask-them-section" data-testid="ask-them-section">
          <div className="ask-them-header">
            <span className="ask-them-badge">Ask them</span>
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

      {/* 8. Show the exact wording: original clause and template excerpt, collapsed by default */}
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

      {/* 9. Read aloud with the browser's speech synthesis, on the device */}
      <footer className="card-read-aloud-footer" data-testid="read-aloud-section">
        <ReadAloudButton text={speechText} />
      </footer>
    </article>
  );
};
