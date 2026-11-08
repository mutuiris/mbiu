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
import { isHighImpactClause } from "@/lib/impact";
import { outcomeLabel } from "@/lib/outcome";
import { openEvaluationReportPdf } from "@/lib/report-pdf";
import { ProgressBar } from "./ProgressBar";
import { ClauseList } from "./ClauseList";
import { ClauseCard, type LinkedClauseItem } from "./ClauseCard";
import { CollapsedMatches } from "./CollapsedMatches";
import { ClauseFailedCard } from "./ClauseFailedCard";
import { ServiceUnavailableBanner } from "./ServiceUnavailableBanner";
import { SummaryCard } from "./SummaryCard";
import { ContractIssuesPanel } from "./ContractIssuesPanel";
import { EvaluationReportModal } from "./EvaluationReportModal";

const MAX_FEATURED_CLAUSES = 2;

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
   * Pre-accumulated evaluation events log from the parent page, allowing
   * immediate restoration of all cards, maps, and document without waiting.
   */
  initialLog?: ReadonlyMap<string, EvaluationEvent> | null;
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
  initialLog = null,
  onRetryClause,
  onRetryAll,
  initialDocument = null,
  file = null,
}) => {
  const [document, setDocument] = useState<DocumentPayload | null>(() => {
    if (initialDocument) return initialDocument;
    const docEvent = initialLog?.get("document");
    return docEvent?.type === "document" ? docEvent.payload : null;
  });
  const [contractMap, setContractMap] = useState<ContractMapPayload | null>(() => {
    const mapEvent = initialLog?.get("contract_map");
    return mapEvent?.type === "contract_map" ? mapEvent.payload : null;
  });
  const [progress, setProgress] = useState<Progress | null>(null);
  const [allResults, setAllResults] = useState<ClauseResult[]>(() => {
    if (!initialLog) return [];
    const list: ClauseResult[] = [];
    for (const ev of initialLog.values()) {
      if (ev.type === "clause_result" || ev.type === "clause_updated") {
        list.push(ev.payload);
      }
    }
    return list;
  });
  const [failures, setFailures] = useState<ClauseFailure[]>(() => {
    if (!initialLog) return [];
    const list: ClauseFailure[] = [];
    for (const ev of initialLog.values()) {
      if (ev.type === "clause_failed") {
        list.push(ev.payload);
      }
    }
    return list;
  });
  const [updatedClauseIds, setUpdatedClauseIds] = useState<Set<string>>(new Set());
  const [summary, setSummary] = useState<Summary | null>(() => {
    const doneEvent = initialLog?.get("done");
    return doneEvent?.type === "done" ? doneEvent.payload : null;
  });
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryingClauseId, setRetryingClauseId] = useState<string | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [viewerClauseId, setViewerClauseId] = useState<string | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);

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

  // Clause IDs involved in contract-wide issues (conflicts/overrides)
  const issueClauseIds = useMemo(() => {
    const set = new Set<string>();
    if (contractMap?.issues) {
      for (const issue of contractMap.issues) {
        issue.clause_ids.forEach((id) => set.add(id));
      }
    }
    return set;
  }, [contractMap]);

  // Partition evaluated clauses into high-impact cards vs remaining clauses
  const { highImpactResults, typicalCount, unusualCount } = useMemo(() => {
    const high: ClauseResult[] = [];
    let typical = 0;
    let unusual = 0;
    for (const r of allResults) {
      const { tone } = outcomeLabel(r.comparison);
      if (tone === "typical") typical++;
      else if (tone === "unusual") unusual++;

      const extra = clauseLookup.get(r.clause_id);
      const hasIssue = issueClauseIds.has(r.clause_id);
      if (isHighImpactClause(r, extra?.heading, hasIssue)) {
        high.push(r);
      }
    }
    return {
      highImpactResults: sortByImpactOrder(high),
      typicalCount: typical,
      unusualCount: unusual,
    };
  }, [allResults, clauseLookup, issueClauseIds]);

  // Only clauses that actually match standard contract templates (typical tone)
  const typicalMatches = useMemo(() => {
    return allResults.filter((r) => outcomeLabel(r.comparison).tone === "typical");
  }, [allResults]);

  // Show at most 2 important clauses on the main page (plus any explicitly selected clause)
  const visibleHighImpactResults = useMemo(() => {
    const topTwo = highImpactResults.slice(0, MAX_FEATURED_CLAUSES);
    if (!selectedClauseId) return topTwo;
    if (topTwo.some((r) => r.clause_id === selectedClauseId)) return topTwo;
    const selectedFromAll = allResults.find((r) => r.clause_id === selectedClauseId);
    return selectedFromAll ? [...topTwo, selectedFromAll] : topTwo;
  }, [highImpactResults, allResults, selectedClauseId]);

  // Results map for overview badges
  const resultsByClauseId = useMemo(() => {
    const map = new Map<string, ClauseResult>();
    for (const r of allResults) {
      map.set(r.clause_id, r);
    }
    return map;
  }, [allResults]);

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
        setAllResults((prev) => {
          const exists = prev.some((r) => r.clause_id === item.clause_id);
          return exists ? prev.map((r) => (r.clause_id === item.clause_id ? item : r)) : [...prev, item];
        });
        setFailures((prev) => prev.filter((f) => f.clause_id !== item.clause_id));
        break;
      }

      case "clause_updated": {
        const item = event.payload;
        setUpdatedClauseIds((prev) => new Set(prev).add(item.clause_id));
        setAllResults((prev) => {
          const exists = prev.some((r) => r.clause_id === item.clause_id);
          return exists ? prev.map((r) => (r.clause_id === item.clause_id ? item : r)) : [...prev, item];
        });
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
    setTimeout(() => {
      const target =
        window.document.getElementById(`card-${clauseId}`) ??
        window.document.getElementById(`clause-item-${clauseId}`);
      if (!target) return;
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    }, 30);
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

  const totalEvaluated = allResults.length + failures.length;
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
    setIsViewerOpen((wasOpen) => {
      if (!wasOpen && typeof window !== "undefined") {
        window.history.pushState({ mbiuOverlay: "contract-viewer" }, "");
      }
      return true;
    });
  }, []);

  const closeViewer = useCallback(() => {
    setIsViewerOpen(false);
    if (
      typeof window !== "undefined" &&
      window.history.state &&
      window.history.state.mbiuOverlay === "contract-viewer"
    ) {
      window.history.back();
    }
    // Back to the card the artist came from
    if (viewerClauseId) handleSelectClause(viewerClauseId);
  }, [viewerClauseId, handleSelectClause]);

  // Intercept phone/browser Back button when mobile contract viewer or report modal is open
  useEffect(() => {
    if (!isViewerOpen && !isReportOpen) return;
    const handlePopState = () => {
      if (isViewerOpen) {
        setIsViewerOpen(false);
      }
      if (isReportOpen) {
        setIsReportOpen(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isViewerOpen, isReportOpen]);

  const handleOpenPdfReport = useCallback(
    (download = false) => {
      openEvaluationReportPdf(
        {
          document,
          allResults,
          highImpactResults,
          contractMap,
          summary,
          clauseLookup,
          isStreaming,
        },
        { download },
      );
    },
    [document, allResults, highImpactResults, contractMap, summary, clauseLookup, isStreaming],
  );

  const remainingEvaluatedCount = Math.max(
    0,
    allResults.length - visibleHighImpactResults.length,
  );

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

        {/* Results Actions Bar (Open / Download PDF Report in New Tab) */}
        {(allResults.length > 0 || isStreaming || document) && (
          <div className="results-actions-bar">
            <button
              type="button"
              onClick={() => handleOpenPdfReport(false)}
              className="download-report-btn"
              data-testid="download-report-btn"
              aria-label="Open evaluation report as PDF in a new tab"
            >
              📄 Download Report (PDF)
            </button>
          </div>
        )}

        {/* Progress Bar */}
        <ProgressBar
          progress={progress}
          isStreaming={isStreaming}
          totalClauses={document?.clauses.length}
          evaluatedCount={totalEvaluated}
        />

        {/* Evaluation Summary Card displayed prominently at the top */}
        {summary && (
          <SummaryCard
            summary={summary}
            typicalCount={typicalCount || summary.matches_count}
            unusualCount={unusualCount}
          />
        )}

        {/* Document Clause Overview (Expanded during streaming, collapsed when done) */}
        {document && (
          <ClauseList
            document={document}
            resultsByClauseId={resultsByClauseId}
            failedByClauseId={failedByClauseId}
            selectedClauseId={selectedClauseId}
            onSelectClause={handleSelectClause}
            isStreaming={isStreaming}
          />
        )}

        {/* Contract-Wide Issues Panel (Sits above clause cards, highest danger first) */}
        {contractMap && contractMap.issues && contractMap.issues.length > 0 && (
          <ContractIssuesPanel
            issues={contractMap.issues}
            clauseLookup={clauseLookup}
            onSelectClause={handleSelectClause}
          />
        )}

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

        {/* Top 2 Most Important Evaluated Clause Cards */}
        {visibleHighImpactResults.length > 0 && (
          <section
            className="results-cards-feed"
            aria-label="Key Clauses to Review First"
          >
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-serif text-[1.25rem] font-semibold tracking-tight text-mbiu-ink dark:text-[#F6F2E9]">
                Key Clauses to Review First ({visibleHighImpactResults.length} of{" "}
                {allResults.length} evaluated)
              </h2>
            </div>
            {visibleHighImpactResults.map((result) => {
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
        )}

        {/* Prompt to Open / Download the PDF Report for the Rest of the Evaluation */}
        {allResults.length > 0 && (
          <section
            className="evaluation-summary-card"
            aria-label="Full Evaluation Report Download"
            data-testid="full-report-prompt"
          >
            <h3 className="summary-title">
              {remainingEvaluatedCount > 0
                ? `Read the remaining ${remainingEvaluatedCount} evaluated ${
                    remainingEvaluatedCount === 1 ? "clause" : "clauses"
                  } in your full PDF report`
                : "Download your full PDF evaluation report"}
            </h3>
            <p className="summary-subtitle" style={{ marginTop: "0.4rem", lineHeight: 1.55 }}>
              To keep this page easy to read, Mbiu highlights the top{" "}
              {Math.min(MAX_FEATURED_CLAUSES, visibleHighImpactResults.length)} most important
              clauses above. Open the full PDF report in a new tab to review every evaluated
              clause, missing protections, and a printable negotiation checklist.
            </p>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "0.75rem",
                marginTop: "1rem",
              }}
            >
              <button
                type="button"
                onClick={() => handleOpenPdfReport(false)}
                className="download-report-btn"
              >
                📄 Open Full Report (PDF in new tab)
              </button>
              <button
                type="button"
                onClick={() => handleOpenPdfReport(true)}
                className="secondary-btn"
              >
                ⬇ Download PDF File
              </button>
            </div>
          </section>
        )}

        {/* Collapsed Typical Clauses Banner (only rendered when typical matches exist) */}
        {typicalMatches.length > 0 && (
          <CollapsedMatches
            matches={typicalMatches}
            clauseLookup={clauseLookup}
            onSelectClause={handleSelectClause}
            selectedClauseId={selectedClauseId}
          />
        )}
      </div>
      {file && (
        <ContractViewer
          file={file}
          clause={viewerClause}
          isOpen={isViewerOpen}
          onClose={closeViewer}
        />
      )}

      {/* Downloadable / Printable Evaluation Report Modal */}
      <EvaluationReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        document={document}
        allResults={allResults}
        highImpactResults={highImpactResults}
        contractMap={contractMap}
        summary={summary}
        clauseLookup={clauseLookup}
        isStreaming={isStreaming}
      />
    </div>
  );
};
