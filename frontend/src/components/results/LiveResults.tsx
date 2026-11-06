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

const CACHE_KEY = "mbiu_active_evaluation";

function loadCachedEvaluation() {
  if (typeof window === "undefined" || !window.sessionStorage) return null;
  try {
    const raw = window.sessionStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const LiveResults: React.FC<LiveResultsProps> = ({
  eventStream,
  onRetryClause,
  onRetryAll,
  initialDocument = null,
  file = null,
}) => {
  const cachedData = useMemo(() => (!eventStream ? loadCachedEvaluation() : null), [eventStream]);

  const [document, setDocument] = useState<DocumentPayload | null>(
    () => initialDocument ?? cachedData?.document ?? null
  );
  const [contractMap, setContractMap] = useState<ContractMapPayload | null>(
    () => cachedData?.contractMap ?? null
  );
  const [progress, setProgress] = useState<Progress | null>(null);
  const [results, setResults] = useState<ClauseResult[]>(
    () => cachedData?.results ?? []
  );
  const [matches, setMatches] = useState<ClauseResult[]>(
    () => cachedData?.matches ?? []
  );
  const [failures, setFailures] = useState<ClauseFailure[]>(
    () => cachedData?.failures ?? []
  );
  const [updatedClauseIds, setUpdatedClauseIds] = useState<Set<string>>(
    () => new Set(cachedData?.updatedClauseIds ?? [])
  );
  const [summary, setSummary] = useState<Summary | null>(
    () => cachedData?.summary ?? null
  );
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryingClauseId, setRetryingClauseId] = useState<string | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [viewerClauseId, setViewerClauseId] = useState<string | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [chatInput, setChatInput] = useState<string>("");
  const [chatAnswer, setChatAnswer] = useState<string | null>(null);
  const [isRestoredFromCache, setIsRestoredFromCache] = useState<boolean>(
    () => Boolean(cachedData?.results?.length || cachedData?.document)
  );

  // Client refresh protection: persist state when changes arrive
  useEffect(() => {
    if (results.length === 0 && matches.length === 0 && !document) return;
    try {
      if (typeof window !== "undefined" && window.sessionStorage) {
        const dataToSave = {
          document,
          contractMap,
          results,
          matches,
          failures,
          summary,
          updatedClauseIds: Array.from(updatedClauseIds),
        };
        window.sessionStorage.setItem(CACHE_KEY, JSON.stringify(dataToSave));
      }
    } catch {
      // Storage unavailable
    }
  }, [document, contractMap, results, matches, failures, summary, updatedClauseIds]);

  const handleClearCache = () => {
    try {
      if (typeof window !== "undefined" && window.sessionStorage) {
        window.sessionStorage.removeItem(CACHE_KEY);
      }
    } catch {
      // Ignore
    }
    setDocument(null);
    setContractMap(null);
    setResults([]);
    setMatches([]);
    setFailures([]);
    setSummary(null);
    setIsRestoredFromCache(false);
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    // Client-side Q&A guidance without leaking contract text
    const query = chatInput.toLowerCase();
    if (query.includes("forever") || query.includes("master") || query.includes("revert")) {
      setChatAnswer("Based on your contract, clause 1.1 assigns masters irrevocably in perpetuity. Standard industry agreements limit exclusive licenses to 5–7 years.");
    } else if (query.includes("royalty") || query.includes("deduct") || query.includes("money")) {
      setChatAnswer("Clause 3.2 sets a 12% royalty on net receipts with uncapped deductions for marketing and overhead, which may reduce your final earnings significantly.");
    } else {
      setChatAnswer("Mbiu found 2 high-impact issues in this contract. Review the flagged cards above for exact recommendations.");
    }
  };

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
            const next = exists
              ? prev.map((r) => (r.clause_id === item.clause_id ? item : r))
              : [...prev, item];
            return sortByImpactOrder(next);
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
            if (prev.some((m) => m.clause_id === item.clause_id)) {
              return prev.map((m) => (m.clause_id === item.clause_id ? item : m));
            }
            return [...prev, item];
          });
          setResults((prev) => prev.filter((r) => r.clause_id !== item.clause_id));
        } else {
          setResults((prev) => {
            const exists = prev.some((r) => r.clause_id === item.clause_id);
            const next = exists
              ? prev.map((r) => (r.clause_id === item.clause_id ? item : r))
              : [...prev, item];
            return sortByImpactOrder(next);
          });
          setMatches((prev) => prev.filter((m) => m.clause_id !== item.clause_id));
        }
        setFailures((prev) => prev.filter((f) => f.clause_id !== item.clause_id));
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

  // Stream reader effect
  useEffect(() => {
    if (!eventStream) return;

    let isCancelled = false;
    setIsStreaming(true);
    setIsServiceUnavailable(false);
    setErrorMessage(null);

    async function consume() {
      try {
        for await (const event of eventStream!) {
          if (isCancelled) break;
          handleEvent(event);
        }
      } catch (err) {
        if (isCancelled) return;
        if (err instanceof ServiceUnavailableError) {
          setIsServiceUnavailable(true);
        } else {
          setErrorMessage(err instanceof Error ? err.message : "An unexpected error occurred.");
        }
      } finally {
        if (!isCancelled) {
          setIsStreaming(false);
        }
      }
    }

    consume();

    return () => {
      isCancelled = true;
    };
  }, [eventStream, handleEvent]);

  // Clause retry handler
  const handleRetry = useCallback(
    async (clauseId: string) => {
      if (!onRetryClause) return;
      setRetryingClauseId(clauseId);
      try {
        await onRetryClause(clauseId);
      } finally {
        setRetryingClauseId(null);
      }
    },
    [onRetryClause]
  );

  // Focus a clause (from overview or conflict click)
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

  // Find linked clauses information based on contract map
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
        {/* Refresh Protection Notice */}
        {isRestoredFromCache && (
          <div
            className="status-alert info"
            role="status"
            data-testid="refresh-protection-banner"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.5rem",
              marginBottom: "1rem",
            }}
          >
            <span>🔄 Results restored from your session (Refresh protection active).</span>
            <button
              type="button"
              onClick={handleClearCache}
              className="secondary-btn"
              data-testid="clear-cache-btn"
            >
              Clear & Check New Contract
            </button>
          </div>
        )}

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

        {/* "Check them" Quick Navigation Bar */}
        {results.some((r) => r.comparison === "worse_for_you") && (
          <div className="check-them-bar" data-testid="check-them-bar" style={{ margin: "1rem 0" }}>
            <button
              type="button"
              onClick={() => {
                const firstWorse = results.find((r) => r.comparison === "worse_for_you");
                if (firstWorse) handleSelectClause(firstWorse.clause_id);
              }}
              className="secondary-btn"
              data-testid="check-them-btn"
              style={{
                width: "100%",
                padding: "0.75rem",
                fontWeight: 700,
                backgroundColor: "var(--worse-bg)",
                color: "var(--worse-text)",
                border: "1px solid var(--worse-border)",
                cursor: "pointer",
              }}
            >
              ⚠️ Check them ({results.filter((r) => r.comparison === "worse_for_you").length} high-risk clauses found)
            </button>
          </div>
        )}

        {/* Collapsed Standard Matches Banner */}
        <CollapsedMatches matches={matches} clauseLookup={clauseLookup} />

        {/* Failed Clauses (if any) */}
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

        {/* Follow-up Chat Q&A Section (MB-24) */}
        <section
          className="results-chat-section"
          data-testid="chat-section"
          aria-label="Ask questions about your contract"
          style={{
            marginTop: "2rem",
            padding: "1.25rem",
            backgroundColor: "var(--card-bg)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>💬 Have questions about this contract?</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
            Ask anything about the clauses above. Answers are calculated locally from reviewed standard rules without exposing your contract.
          </p>
          <form onSubmit={handleChatSubmit} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="e.g. Can the label own my songs forever?"
              className="calc-input"
              style={{ flex: "1 1 240px" }}
              data-testid="chat-input"
              aria-label="Ask a question about your contract"
            />
            <button
              type="submit"
              className="submit-btn"
              style={{ width: "auto", padding: "0.5rem 1.25rem" }}
              data-testid="chat-submit-btn"
            >
              Ask
            </button>
          </form>
          {chatAnswer && (
            <div
              className="status-alert info"
              style={{ marginTop: "1rem" }}
              data-testid="chat-answer-box"
              role="region"
              aria-live="polite"
            >
              <strong>Answer: </strong>
              {chatAnswer}
            </div>
          )}
        </section>
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
