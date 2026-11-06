"use client";

import React, { useMemo, useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import type {
  DocumentPayload,
  Progress,
  ClauseResult,
  ClauseFailure,
  Summary,
  ContractMapPayload,
} from "@/lib/api/generated/types.gen";
import {
  type EvaluationEvent,
  sortByImpactOrder,
  ServiceUnavailableError,
} from "@/lib/api/stream";
import { ProgressBar } from "./ProgressBar";
import { ClauseList } from "./ClauseList";
import { ClauseCard, type LinkedClauseItem } from "./ClauseCard";
import { CollapsedMatches } from "./CollapsedMatches";
import { ClauseFailedCard } from "./ClauseFailedCard";
import { ServiceUnavailableBanner } from "./ServiceUnavailableBanner";
import { SummaryCard } from "./SummaryCard";
import { ContractIssuesPanel } from "./ContractIssuesPanel";

/** Shown when time or the token budget ran out before every clause was checked. */
export function notCheckedMessage(count: number): string {
  const clauses = count === 1 ? "1 clause isn't" : `${count} clauses aren't`;
  return `Mbiu checked the most important clauses first. ${clauses} checked yet.`;
}

// pdf.js needs the browser, so the viewer is never rendered on the server
const ContractViewer = dynamic(() => import("@/components/viewer/ContractViewer"), { ssr: false });

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
  /**
   * The artist's uploaded file, shown in the contract viewer. Kept in memory only.
   */
  file?: File | null;
}

export const LiveResults: React.FC<LiveResultsProps> = ({
  eventStream,
  onRetryClause,
  onRetryAll,
  initialDocument = null,
  file = null,
}) => {
  const [document, setDocument] = useState<DocumentPayload | null>(initialDocument);
  const [contractMap, setContractMap] = useState<ContractMapPayload | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [results, setResults] = useState<ClauseResult[]>([]);
  const [matches, setMatches] = useState<ClauseResult[]>([]);
  const [failures, setFailures] = useState<ClauseFailure[]>([]);
  const [updatedClauseIds, setUpdatedClauseIds] = useState<Set<string>>(new Set());
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryingClauseId, setRetryingClauseId] = useState<string | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [viewerClauseId, setViewerClauseId] = useState<string | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);

  // Fast clause lookup for numbering, headings, and pages
  const clauseLookup = useMemo(() => {
    const map = new Map<
      string,
      { number?: string | null; heading?: string | null; pages?: number[] }
    >();
    if (document) {
      for (const c of document.clauses) {
        map.set(c.clause_id, { number: c.number, heading: c.heading, pages: c.pages });
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

      case "contract_map":
        setContractMap(event.payload);
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
        setFailures((prev) => prev.filter((f) => f.clause_id !== item.clause_id));
        break;
      }

      case "clause_updated": {
        const item = event.payload;
        setUpdatedClauseIds((prev) => new Set(prev).add(item.clause_id));

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
        break;
    }
  }, []);

  useEffect(() => {
    if (!eventStream) return;

    let cancelled = false;

    const readStream = async () => {
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
          setErrorMessage(
            err instanceof Error ? err.message : "An error occurred during evaluation."
          );
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

  const handleSelectClause = useCallback((clauseId: string) => {
    setSelectedClauseId(clauseId);
    const target =
      window.document.getElementById(`card-${clauseId}`) ??
      window.document.getElementById(`clause-item-${clauseId}`);
    if (!target) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
    // Move keyboard and screen-reader focus to the card, not just the viewport
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  }, []);

  // Compute linked clauses metadata for each card
  const getLinkedClausesFor = useCallback(
    (clauseId: string, directLinks: string[] = []): LinkedClauseItem[] => {
      const set = new Set<string>(directLinks);
      if (contractMap?.links) {
        for (const l of contractMap.links) {
          if (l.from_clause_id === clauseId && l.to_clause_id !== clauseId) {
            set.add(l.to_clause_id);
          } else if (l.to_clause_id === clauseId && l.from_clause_id !== clauseId) {
            set.add(l.from_clause_id);
          }
        }
      }

      const items: LinkedClauseItem[] = [];
      for (const targetId of set) {
        const extra = clauseLookup.get(targetId);
        const label = extra?.number
          ? `Clause ${extra.number}${extra.heading ? ` (${extra.heading})` : ""}`
          : `Clause ${targetId}`;

        const relatedIssue = contractMap?.issues.find(
          (i) => i.clause_ids.includes(clauseId) && i.clause_ids.includes(targetId)
        );

        items.push({
          clauseId: targetId,
          label,
          issueKind: relatedIssue?.kind ?? null,
        });
      }

      return items;
    },
    [contractMap, clauseLookup]
  );

  const totalEvaluated = results.length + matches.length + failures.length;
  const notCheckedCount = failures.filter((f) => f.reason === "not_checked").length;
  // Every clause failed because no provider was reachable: same message as a failed upload
  const isEverythingUnavailable =
    !!document &&
    document.clauses.length > 0 &&
    failures.length === document.clauses.length &&
    failures.every((f) => f.reason === "unavailable");

  const viewerClause = useMemo(() => {
    const clause = document?.clauses.find((c) => c.clause_id === viewerClauseId);
    return clause ? { clauseId: clause.clause_id, pages: clause.pages, text: clause.text } : null;
  }, [document, viewerClauseId]);

  const openInViewer = useCallback((clauseId: string) => {
    setViewerClauseId(clauseId);
    setIsViewerOpen(true);
  }, []);

  const closeViewer = useCallback(() => {
    setIsViewerOpen(false);
    // Back to the card the artist came from
    if (viewerClauseId) handleSelectClause(viewerClauseId);
  }, [viewerClauseId, handleSelectClause]);

  return (
    <div className={`live-results-layout${file ? " has-viewer" : ""}`}>
      <div className="live-results-container">
        {/* Service Unavailable Banner */}
        {(isServiceUnavailable || isEverythingUnavailable) && (
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

        {/* Contract-Wide Issues Panel (Sits above all cards, highest danger first) */}
        {contractMap && contractMap.issues && contractMap.issues.length > 0 && (
          <ContractIssuesPanel
            issues={contractMap.issues}
            clauseLookup={clauseLookup}
            onSelectClause={handleSelectClause}
          />
        )}

        {/* Collapsed Standard Matches Banner */}
        <CollapsedMatches matches={matches} clauseLookup={clauseLookup} />

        {/* Failed Clauses (if any) */}
        {notCheckedCount > 0 && (
          <p className="status-alert info" role="status">
            {notCheckedMessage(notCheckedCount)}
          </p>
        )}

        {failures.length > 0 && (
          <section
            className="failed-clauses-section"
            aria-label="Clauses that could not be checked"
          >
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
        <section
          className="results-cards-feed"
          aria-label="Evaluated Clauses in Impact Order"
        >
          {results.map((result) => {
            const extra = clauseLookup.get(result.clause_id);
            return (
              <ClauseCard
                key={result.clause_id}
                result={result}
                clauseNumber={extra?.number}
                clauseHeading={extra?.heading}
                isHighlighted={selectedClauseId === result.clause_id}
                isUpdated={updatedClauseIds.has(result.clause_id)}
                linkedClauses={getLinkedClausesFor(result.clause_id, result.linked_clauses)}
                onSelectClause={handleSelectClause}
                onJumpToPdfClause={file ? openInViewer : undefined}
              />
            );
          })}
        </section>

        {/* Final Summary Card upon done event */}
        {summary && <SummaryCard summary={summary} />}
      </div>
      {file && (
        <ContractViewer
          file={file}
          clause={viewerClause}
          isOpen={isViewerOpen}
          onClose={closeViewer}
        />
      )}
    </div>
  );
};
