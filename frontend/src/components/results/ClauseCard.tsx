"use client";

import React from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";
import { CopyButton, type CopyButtonProps } from "./CopyButton";
import { SpeechButton, ReadAloudButton, type ReadAloudButtonProps } from "./SpeechButton";
import { CardHeader } from "./CardHeader";
import { CardImpact, type LinkedClauseItem } from "./CardImpact";
import { CardQuestions } from "./CardQuestions";
import { CardWording } from "./CardWording";

export type { CopyButtonProps, ReadAloudButtonProps, LinkedClauseItem };
export { CopyButton, ReadAloudButton, SpeechButton };

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

const BADGE_CLASS: Record<OutcomeTone, string> = {
  typical: "badge-typical",
  unusual: "badge-unusual",
  worth_asking_about: "badge-worth",
  cannot_compare: "badge-cannot-compare",
};

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
  const { label, symbol, tone, display } = outcomeLabel(result.comparison);
  const badge = { label, symbol, tone, display, className: BADGE_CLASS[tone] };

  const formattedClauseNumber = clauseNumber
    ? clauseNumber.trim().toLowerCase().startsWith("clause")
      ? clauseNumber.trim()
      : `Clause ${clauseNumber.trim()}`
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
      aria-labelledby={`heading-${result.clause_id}`}
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

      {/* 1. Heading */}
      <CardHeader
        clauseId={result.clause_id}
        headingTitle={headingTitle}
        badge={badge}
        topicText={topicText}
        locationLabel={locationLabel}
        firstPage={firstPage}
        onJumpToPdfClause={onJumpToPdfClause}
      />

      {/* 2. What your contract says */}
      <section className="card-section card-what-it-says" data-testid="what-it-says-section">
        <h4 className="card-section-title">What your contract says</h4>
        <blockquote className="card-contract-quote text-contract">“{result.what_it_says}”</blockquote>
      </section>

      {/* 3. In plain language */}
      <section className="card-section card-plain-language" data-testid="plain-language-section">
        <h4 className="card-section-title">In plain language</h4>
        <p className="card-plain-language-text" data-testid="clause-headline">{result.headline}</p>
      </section>

      {/* 4. Why this may matter to you */}
      <CardImpact
        whatItMeans={result.what_it_means}
        impactInputs={result.impact_inputs}
        linkedClauses={linkedClauses}
        onSelectClause={onSelectClause}
      />

      {/* 5. How it compares */}
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

      {/* 6. Questions you could ask */}
      <CardQuestions
        askThem={result.ask_them}
        whatsappShareUrl={whatsappShareUrl}
      />

      {/* 7. Sources */}
      {sourcesText && (
        <section className="card-section card-sources-section" data-testid="sources-section">
          <div className="card-sources">
            <span className="sources-title">Sources: </span>
            <span className="sources-content">{sourcesText}</span>
          </div>
        </section>
      )}

      {/* 8. Notice */}
      <div className="card-notice" data-testid="clause-notice">
        <p className="card-notice-disclaimer">
          <em>This explains what the contract says compared with reference material. It doesn’t say whether a clause is lawful or enforceable, and it isn’t legal advice.</em>
        </p>
      </div>

      {/* Raw clause inspection */}
      <CardWording
        originalText={result.original_text}
        standardExcerpt={result.standard_excerpt}
      />

      {/* Read aloud footer */}
      <footer className="card-read-aloud-footer" data-testid="read-aloud-section">
        <SpeechButton text={speechText} />
      </footer>
    </article>
  );
};
