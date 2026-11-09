"use client";

import { Square, Volume2 } from "lucide-react";
import React, { useEffect, useState } from "react";
import type { ClauseResult } from "@/lib/api/generated/types.gen";
import { outcomeLabel } from "@/lib/outcome";
import { cleanReferenceText, displayNumber, readableClauseName } from "@/lib/report";
import { ShillingsCalculator } from "./ShillingsCalculator";
import { Fold, OutcomePill, ReportCard } from "./ui";

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
      className="report-press inline-flex min-h-11 items-center gap-1.5 text-[0.85rem] font-semibold text-mbiu-indigo dark:text-[#a9b0ff]"
      aria-label={isSpeaking ? "Stop reading aloud" : "Read this card aloud"}
    >
      {isSpeaking ? <Square aria-hidden="true" className="h-4 w-4" /> : <Volume2 aria-hidden="true" className="h-4 w-4" />}
      <span>{isSpeaking ? "Stop reading" : "Read aloud"}</span>
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

const LINKS_SHOWN = 3;

const sectionLabel = "text-[0.72rem] font-bold uppercase tracking-[0.08em] text-mbiu-ink/55 dark:text-[#b9c1c5]";
const linkButton =
  "report-press inline-flex min-h-11 items-center text-[0.9rem] font-semibold text-mbiu-indigo underline underline-offset-4 dark:text-[#a9b0ff]";

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
  const [showAllLinks, setShowAllLinks] = useState(false);
  const { label: outcome } = outcomeLabel(result.comparison);
  const name = readableClauseName({
    number: clauseNumber,
    heading: clauseHeading ?? topic,
    text: result.original_text,
  });
  const firstPage = result.pages[0] ?? 1;

  const sources = result.evidence?.length
    ? [...new Set(result.evidence.map((ev) => ev.source_title))].join(" · ")
    : result.standard_template_id;
  const usualWording = result.standard_excerpt ? cleanReferenceText(result.standard_excerpt) : null;
  const comparison = result.comparison_note ?? null;

  const speechText = [
    `${name}. ${outcome}.`,
    `${result.headline}.`,
    `In simple words: ${result.what_it_says}.`,
    `Why it matters: ${result.what_it_means}.`,
    comparison ? `What usual contracts say: ${comparison}.` : "",
    result.ask_them ? `Ask them this: ${result.ask_them}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const whatsappShareUrl = result.ask_them
    ? `https://wa.me/?text=${encodeURIComponent(
        `A question about ${displayNumber(clauseNumber) ? `clause ${displayNumber(clauseNumber)}` : "my contract"}, from Mbiu:\n${result.ask_them}`,
      )}`
    : "";

  const links = showAllLinks ? linkedClauses : linkedClauses.slice(0, LINKS_SHOWN);

  return (
    <ReportCard
      as="article"
      id={`card-${result.clause_id}`}
      aria-labelledby={`heading-${result.clause_id}`}
      data-testid={`card-${result.clause_id}`}
      className={isHighlighted ? "ring-2 ring-mbiu-indigo ring-offset-2 ring-offset-[#fcf4e5] dark:ring-offset-mbiu-bg-dark" : ""}
    >
      <div className="flex items-start justify-between gap-3" data-testid="clause-header">
        <p className="min-w-0 break-words text-[0.88rem] font-semibold text-mbiu-ink/70 dark:text-[#d6dadc]">{name}</p>
        <OutcomePill comparison={result.comparison} />
      </div>

      {isUpdated && (
        <p className="mt-2 text-[0.8rem] font-semibold text-mbiu-indigo dark:text-[#a9b0ff]" role="status" data-testid="clause-updated-notice">
          Result updated based on whole-contract check
        </p>
      )}

      <h3
        id={`heading-${result.clause_id}`}
        className="mt-2 break-words font-serif text-[1.2rem] font-medium leading-snug text-mbiu-ink dark:text-[#F6F2E9]"
        data-testid="clause-headline"
      >
        {result.headline}
      </h3>

      <Fold summary="In simple words">
        <p className="pb-1 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d6dadc]">{result.what_it_says}</p>
      </Fold>

      {/* Laptops show why it matters; phones fold it to keep the report skimmable */}
      <div className="mt-2 hidden lg:block" data-testid="why-it-matters-section">
        <h4 className={sectionLabel}>Why it matters</h4>
        <p className="mt-1 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d6dadc]">{result.what_it_means}</p>
      </div>
      <Fold summary="Why it matters" className="lg:hidden">
        <p className="pb-1 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d6dadc]">{result.what_it_means}</p>
      </Fold>

      <ShillingsCalculator inputs={result.impact_inputs} />

      {(comparison || sources) && (
        <div className="mt-4" data-testid="how-it-compares-section">
          <h4 className={sectionLabel}>What usual contracts say</h4>
          {comparison && (
            <p className="mt-1 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d6dadc]">{comparison}</p>
          )}
          {sources && <p className="mt-1 text-[0.8rem] text-mbiu-ink/55 dark:text-[#b9c1c5]">Compared with: {sources}</p>}
        </div>
      )}

      {result.ask_them && (
        <div className="mt-4 border-l-[3px] border-mbiu-indigo pl-3 dark:border-mbiu-indigo-dark" data-testid="ask-them-section">
          <h4 className="text-[0.72rem] font-bold uppercase tracking-[0.08em] text-mbiu-indigo dark:text-[#a9b0ff]">Ask them this</h4>
          <p className="mt-1 break-words text-[0.98rem] text-mbiu-ink dark:text-[#F4EFE6]">{result.ask_them}</p>
          <div className="mt-1 flex flex-wrap gap-x-5">
            <CopyButton text={result.ask_them} label="Copy" copiedLabel="Copied" className={linkButton} />
            <a href={whatsappShareUrl} target="_blank" rel="noopener noreferrer" className={linkButton}>
              Share on WhatsApp
            </a>
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-start gap-x-5" data-testid="exact-wording-section">
        <Fold summary="See the exact words" className="w-full sm:w-auto">
          <div className="space-y-3 pb-2 text-[0.9rem] text-mbiu-ink/85 dark:text-[#d6dadc]">
            <blockquote className="break-words border-l-2 border-[#e9dec9] pl-3 dark:border-white/15">
              <span className="block text-[0.75rem] font-semibold text-mbiu-ink/55 dark:text-[#b9c1c5]">Your contract</span>
              “{result.original_text}”
            </blockquote>
            {usualWording && (
              <blockquote className="break-words border-l-2 border-[#e9dec9] pl-3 dark:border-white/15">
                <span className="block text-[0.75rem] font-semibold text-mbiu-ink/55 dark:text-[#b9c1c5]">Usual contract wording</span>
                “{usualWording}”
              </blockquote>
            )}
          </div>
        </Fold>
        {onJumpToPdfClause && (
          <button type="button" onClick={() => onJumpToPdfClause(result.clause_id, firstPage)} className={linkButton}>
            View on page {firstPage}
          </button>
        )}
      </div>

      {linkedClauses.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 text-[0.85rem] text-mbiu-ink/60 dark:text-[#b9c1c5]" data-testid="also-affected-by">
          <span>Linked:</span>
          {links.map((link) => (
            <button
              key={link.clauseId}
              type="button"
              onClick={() => onSelectClause?.(link.clauseId)}
              className={linkButton}
              aria-label={`Go to ${link.label}`}
            >
              {link.label}
            </button>
          ))}
          {!showAllLinks && linkedClauses.length > LINKS_SHOWN && (
            <button type="button" onClick={() => setShowAllLinks(true)} className={linkButton}>
              +{linkedClauses.length - LINKS_SHOWN}
            </button>
          )}
        </div>
      )}

      <footer className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[#e9dec9] pt-2 dark:border-white/10" data-testid="read-aloud-section">
        <p className="text-[0.78rem] text-mbiu-ink/55 dark:text-[#b9c1c5]" data-testid="clause-notice">
          Not legal advice.
        </p>
        <ReadAloudButton text={speechText} />
      </footer>
    </ReportCard>
  );
};
