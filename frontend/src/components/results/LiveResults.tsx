"use client";

import React, { useMemo, useState, useCallback, useEffect } from "react";
import type {
  DocumentPayload,
  Progress,
  ClauseResult,
  ClauseFailure,
  Summary,
} from "@/lib/api/generated/types.gen";
import {
  type EvaluationEvent,
  sortByImpactOrder,
  ServiceUnavailableError,
} from "@/lib/api/stream";
import { ProgressBar } from "./ProgressBar";
import { ClauseList } from "./ClauseList";
import { ClauseCard } from "./ClauseCard";
import { CollapsedMatches } from "./CollapsedMatches";
import { ClauseFailedCard } from "./ClauseFailedCard";
import { ServiceUnavailableBanner } from "./ServiceUnavailableBanner";
import { SummaryCard } from "./SummaryCard";

export interface LiveResultsProps {
  /**
   * An optional async generator stream to consume automatically on mount.
   */
  eventStream?: AsyncGenerator<EvaluationEvent, void, unknown> | null;
  /**
   * Callback when a failed clause is retried by the user.
   */
  onRetryClause?: (clauseId: string) => Promise<void> | void;
  /**
   * Callback when "Try Again" is clicked on service unavailable state.
   */
  onRetryAll?: () => void;
  /**
   * Initial document if already split.
   */
  initialDocument?: DocumentPayload | null;
}

export const LiveResults: React.FC<LiveResultsProps> = ({
  eventStream,
  onRetryClause,
  onRetryAll,
  initialDocument = null,
}) => {
  const [document, setDocument] = useState<DocumentPayload | null>(initialDocument);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [results, setResults] = useState<ClauseResult[]>([]);
  const [matches, setMatches] = useState<ClauseResult[]>([]);
  const [failures, setFailures] = useState<ClauseFailure[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryingClauseId, setRetryingClauseId] = useState<string | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);

  // Fast clause lookup for numbering and headings
  const clauseLookup = useMemo(() => {
    const map = new Map<string, { number?: string | null; heading?: string | null }>();
    if (document) {
      for (const c of document.clauses) {
        map.set(c.clause_id, { number: c.number, heading: c.heading });
      }
    }
    return map;
  }, [document]);

  // Results map for overview badges
  const resultsByClauseId = useMemo(() => {
    const map = new Map<string, ClauseResult>();
    for (const r of results) {
      map.set(r.clause_id, r);
    }
    for (const m of matches) {
      map.set(m.clause_id, m);
    }
    return map;
  }, [results, matches]);

  // Failures map for overview badges
  const failedByClauseId = useMemo(() => {
    const map = new Map<string, ClauseFailure>();
    for (const f of failures) {
      map.set(f.clause_id, f);
    }
    return map;
  }, [failures]);

  // Handle single incoming stream event
  const handleEvent = useCallback((event: EvaluationEvent) => {
    switch (event.type) {
      case "document":
        setDocument(event.payload);
        break;

      case "progress":
        setProgress(event.payload);
        break;

      case "clause_result": {
        const item = event.payload;
        if (item.comparison === "matches_standard") {
          setMatches((prev) => {
            if (prev.some((m) => m.clause_id === item.clause_id)) {
              return prev.map((m) => (m.clause_id === item.clause_id ? item : m));
            }
            return [...prev, item];
          });
          // Remove from results if it was previously categorized differently
          setResults((prev) => prev.filter((r) => r.clause_id !== item.clause_id));
        } else {
          setResults((prev) => {
            const exists = prev.some((r) => r.clause_id === item.clause_id);
            const updated = exists
              ? prev.map((r) => (r.clause_id === item.clause_id ? item : r))
              : [...prev, item];
            // Immediately sort in impact order as cards arrive
            return sortByImpactOrder(updated);
          });
          // Remove from matches if it was previously in matches
          setMatches((prev) => prev.filter((m) => m.clause_id !== item.clause_id));
        }
        // If it was marked failed, clear failure now that result arrived
        setFailures((prev) => prev.filter((f) => f.clause_id !== item.clause_id));
        break;
      }

      case "clause_updated": {
        const item = event.payload;
        if (item.comparison === "matches_standard") {
          setMatches((prev) => {
            const exists = prev.some((m) => m.clause_id === item.clause_id);
            return exists
              ? prev.map((m) => (m.clause_id === item.clause_id ? item : m))
              : [...prev, item];
          });
          setResults((prev) => prev.filter((r) => r.clause_id !== item.clause_id));
        } else {
          setResults((prev) => {
            const exists = prev.some((r) => r.clause_id === item.clause_id);
            const updated = exists
              ? prev.map((r) => (r.clause_id === item.clause_id ? item : r))
              : [...prev, item];
            return sortByImpactOrder(updated);
          });
          setMatches((prev) => prev.filter((m) => m.clause_id !== item.clause_id));
        }
        break;
      }

      case "clause_failed": {
        const failure = event.payload;
        setFailures((prev) => {
          if (prev.some((f) => f.clause_id === failure.clause_id)) {
            return prev.map((f) => (f.clause_id === failure.clause_id ? failure : f));
          }
          return [...prev, failure];
        });
        break;
      }

      case "done":
        setSummary(event.payload);
        setIsStreaming(false);
        break;

      default:
        // Ignore unhandled events
        break;
    }
  }, []);

  useEffect(() => {
    if (!eventStream) return;

    let cancelled = false;

    const readStream = async () => {
      // Yield execution so setState is called in the event loop, not synchronously in the effect
      await Promise.resolve();
      if (cancelled) return;

      setIsStreaming(true);
      setErrorMessage(null);
      setIsServiceUnavailable(false);

      try {
        for await (const event of eventStream) {
          if (cancelled) break;
          handleEvent(event);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ServiceUnavailableError) {
          setIsServiceUnavailable(true);
        } else {
          setErrorMessage(err instanceof Error ? err.message : "An error occurred during evaluation.");
        }
      } finally {
        if (!cancelled) {
          setIsStreaming(false);
        }
      }
    };

    void readStream();

    return () => {
      cancelled = true;
    };
  }, [eventStream, handleEvent]);

  const handleRetry = async (clauseId: string) => {
    setRetryingClauseId(clauseId);
    try {
      if (onRetryClause) {
        await onRetryClause(clauseId);
      }
    } finally {
      setRetryingClauseId(null);
    }
  };

  const handleSelectClause = (clauseId: string) => {
    setSelectedClauseId(clauseId);
    const cardElement = window.document.getElementById(`card-${clauseId}`);
    if (cardElement) {
      cardElement.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  const totalEvaluated = results.length + matches.length + failures.length;

  return (
    <div className="live-results-container">
      {/* Service Unavailable Banner */}
      {isServiceUnavailable && (
        <ServiceUnavailableBanner onRetryAll={onRetryAll} />
      )}

      {/* General Error Alert */}
      {errorMessage && (
        <div className="status-alert error" role="alert">
          <strong>Error: </strong>
          {errorMessage}
        </div>
      )}

      {/* Progress Bar */}
      <ProgressBar
        progress={progress}
        isStreaming={isStreaming}
        totalClauses={document?.clauses.length}
        evaluatedCount={totalEvaluated}
      />

      {/* Document Clause Overview (Visible as soon as document event arrives) */}
      {document && (
        <ClauseList
          document={document}
          resultsByClauseId={resultsByClauseId}
          failedByClauseId={failedByClauseId}
          selectedClauseId={selectedClauseId}
          onSelectClause={handleSelectClause}
        />
      )}

      {/* Collapsed Standard Matches Banner */}
      <CollapsedMatches matches={matches} clauseLookup={clauseLookup} />

      {/* Failed Clauses (if any) */}
      {failures.length > 0 && (
        <section className="failed-clauses-section" aria-label="Clauses that could not be checked">
          {failures.map((f) => {
            const extra = clauseLookup.get(f.clause_id);
            return (
              <ClauseFailedCard
                key={f.clause_id}
                failure={f}
                clauseNumber={extra?.number}
                clauseHeading={extra?.heading}
                onRetry={handleRetry}
                isRetrying={retryingClauseId === f.clause_id}
              />
            );
          })}
        </section>
      )}

      {/* Evaluated Clause Cards (Shown in strict impact order: highest risk first) */}
      <section className="results-cards-feed" aria-label="Evaluated Clauses in Impact Order">
        {results.map((result) => {
          const extra = clauseLookup.get(result.clause_id);
          return (
            <ClauseCard
              key={result.clause_id}
              result={result}
              clauseNumber={extra?.number}
              clauseHeading={extra?.heading}
              isHighlighted={selectedClauseId === result.clause_id}
            />
          );
        })}
      </section>

      {/* Final Summary Card upon done event */}
      {summary && <SummaryCard summary={summary} />}
    </div>
  );
};
