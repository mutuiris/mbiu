"use client";

import React, { useMemo, useState, useCallback, useEffect, type ReactNode } from "react";
import dynamic from "next/dynamic";
import type {
  DocumentPayload,
  ClauseResult,
  ClauseFailure,
  Summary,
  ContractMapPayload,
} from "@/lib/api/generated/types.gen";
import {
  type EvaluationEvent,
  ServiceUnavailableError,
} from "@/lib/api/stream";
import { displayNumber, groupResults, readableClauseName } from "@/lib/report";
import { ClauseSection } from "./ClauseSection";
import { ReportHeader } from "./ReportHeader";
import { Button, Fold, ReportCard } from "./ui";
import { Download } from "lucide-react";
import { QuestionsToAsk } from "./QuestionsToAsk";
import { ClauseList } from "./ClauseList";
import { ClauseCard, type LinkedClauseItem } from "./ClauseCard";
import { ClauseFailedCard } from "./ClauseFailedCard";
import { ServiceUnavailableBanner } from "./ServiceUnavailableBanner";
import { SummaryCard } from "./SummaryCard";
import { ContractIssuesPanel } from "./ContractIssuesPanel";
import { downloadReport, reportData } from "@/components/report-pdf/download";

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
  /** Starts over with another contract. */
  onCheckAnother?: () => void;
  /** Clauses the page can still check; shown as "Check the other N". */
  notChecked?: number;
  onCheckRest?: () => void;
  /** The keep-results switch, owned by the page. */
  keep?: ReactNode;
}

const sentenceCase = (text: string) =>
  text.length > 0 ? text[0].toUpperCase() + text.slice(1).toLowerCase() : text;

export const LiveResults: React.FC<LiveResultsProps> = ({
  eventStream,
  onRetryClause,
  onRetryAll,
  initialDocument = null,
  file = null,
  onCheckAnother,
  notChecked = 0,
  onCheckRest,
  keep = null,
}) => {
  const [document, setDocument] = useState<DocumentPayload | null>(initialDocument);
  const [contractMap, setContractMap] = useState<ContractMapPayload | null>(null);
  const [allResults, setAllResults] = useState<ClauseResult[]>([]);
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
  const [downloadState, setDownloadState] = useState<"idle" | "preparing" | "saved" | "failed">("idle");

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

  const grouped = useMemo(
    () => groupResults(allResults, clauseLookup, issueClauseIds),
    [allResults, clauseLookup, issueClauseIds],
  );

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

  const documentTitle = useMemo(() => {
    const heading = document?.clauses.find((c) => c.heading)?.heading?.trim();
    return heading ? sentenceCase(heading) : null;
  }, [document]);

  // Handle single incoming stream event
  const handleEvent = useCallback((event: EvaluationEvent) => {
    switch (event.type) {
      case "document":
        setDocument(event.payload);
        break;

      case "contract_map":
        setContractMap(event.payload);
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
    const find = () => {
      const card = window.document.getElementById(`card-${clauseId}`);
      return card && !card.closest("[hidden]") ? card : window.document.getElementById(`clause-item-${clauseId}`);
    };
    const scrollTo = (target: HTMLElement) => {
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
      // Move keyboard and screen-reader focus to the card, not just the viewport
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    };
    // A clause inside a closed fold: let the fold open (200 ms) before scrolling, or the page is
    // still too short and the scroll stops early
    const wasFolded = !!find()?.closest("[hidden]");
    window.setTimeout(
      () => {
        const target = find();
        if (target) scrollTo(target);
      },
      wasFolded ? 260 : 0,
    );
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
        const label = displayNumber(extra?.number) ?? readableClauseName(extra);

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

  const notCheckedNames = useMemo(() => {
    if (!document || isStreaming) return [];
    const realFailures = new Set(failures.filter((f) => f.reason !== "not_checked").map((f) => f.clause_id));
    return document.clauses
      .filter((c) => !resultsByClauseId.has(c.clause_id) && !realFailures.has(c.clause_id))
      .map((c) => readableClauseName(c));
  }, [document, isStreaming, failures, resultsByClauseId]);
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

  const handleDownload = useCallback(async () => {
    if (downloadState === "preparing") return;
    setDownloadState("preparing");
    try {
      await downloadReport(
        reportData({
          document,
          results: allResults,
          cards: grouped.writeUps,
          contractMap,
          summary,
          clauseLookup,
          isStreaming,
          today: new Date(),
        }),
      );
      setDownloadState("saved");
    } catch (error) {
      console.error("Report PDF failed", error);
      setDownloadState("failed");
    }
    setTimeout(() => setDownloadState("idle"), 2500);
  }, [downloadState, document, allResults, grouped.writeUps, contractMap, summary, clauseLookup, isStreaming]);

  const downloadLabel = {
    idle: "Download report (PDF)",
    preparing: "Preparing…",
    saved: "Saved",
    failed: "Couldn't make the PDF. Try again",
  }[downloadState];

  return (
    <div className={`live-results-layout pb-24 lg:pb-0${file ? " has-viewer" : ""}`}>
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

        {(document || isStreaming) && (
          <ReportHeader
            documentTitle={documentTitle}
            pageCount={document?.page_count ?? null}
            checked={allResults.length}
            total={document?.clauses.length ?? 0}
            isStreaming={isStreaming}
            counts={grouped.counts}
            notChecked={notChecked}
            onCheckRest={onCheckRest}
            onDownload={handleDownload}
            downloadLabel={downloadLabel}
            onCheckAnother={onCheckAnother ?? (() => onRetryAll?.())}
            keep={keep}
          />
        )}

        {summary && summary.top_asks.length > 0 && (
          <QuestionsToAsk
            asks={summary.top_asks}
            clauseLookup={clauseLookup}
            onView={file ? openInViewer : handleSelectClause}
          />
        )}

        {contractMap && contractMap.issues && contractMap.issues.length > 0 && (
          <ContractIssuesPanel
            issues={contractMap.issues}
            clauseLookup={clauseLookup}
            onSelectClause={handleSelectClause}
          />
        )}

        <ClauseSection
          grouped={grouped}
          renderCard={(result, index) => {
            const extra = clauseLookup.get(result.clause_id);
            return (
              <div
                key={result.clause_id}
                className="report-arrive"
                style={{ "--arrive-index": Math.min(index, 8) } as React.CSSProperties}
              >
                <ClauseCard
                  result={result}
                  clauseNumber={extra?.number}
                  clauseHeading={extra?.heading}
                  isHighlighted={selectedClauseId === result.clause_id}
                  isUpdated={updatedClauseIds.has(result.clause_id)}
                  linkedClauses={getLinkedClausesFor(result.clause_id, result.linked_clauses)}
                  onSelectClause={handleSelectClause}
                  onJumpToPdfClause={file ? openInViewer : undefined}
                />
              </div>
            );
          }}
          failedCards={failures
            .filter((f) => f.reason !== "not_checked")
            .map((f) => {
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
          notCheckedNames={notCheckedNames}
          onCheckRest={onCheckRest}
          selectedClauseId={selectedClauseId}
        />

        {/* Final Summary Card upon done event */}
        {summary && <SummaryCard summary={summary} />}

        {document && (
          <ReportCard>
            <Fold
              summary={`All ${document.clauses.length} clauses`}
              forceOpen={!!selectedClauseId && !resultsByClauseId.has(selectedClauseId)}
            >
              <ClauseList
                document={document}
                resultsByClauseId={resultsByClauseId}
                failedByClauseId={failedByClauseId}
                selectedClauseId={selectedClauseId}
                onSelectClause={handleSelectClause}
              />
            </Fold>
          </ReportCard>
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

      {document && !isViewerOpen && (
        <div className="fixed inset-x-0 bottom-0 z-40 bg-gradient-to-t from-[#fcf4e5] via-[#fcf4e5]/95 to-transparent px-4 pb-4 pt-6 lg:hidden dark:from-mbiu-bg-dark dark:via-mbiu-bg-dark/95">
          <Button variant="primary" className="w-full" onClick={handleDownload} aria-live="polite">
            <Download aria-hidden="true" className="h-4 w-4" />
            {downloadLabel}
          </Button>
        </div>
      )}

    </div>
  );
};
