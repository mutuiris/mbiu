/**
 * Refresh protection and resuming unfinished clauses (MB-26).
 *
 * Implements the three layers of protection:
 * 1. Prevent accidental refresh:
 *    - beforeunload confirmation dialog while results or chat are on screen.
 *    - CSS overscroll-behavior-y: contain to prevent accidental pull-to-refresh on mobile.
 * 2. Keep tab state:
 *    - Interacts with keep-tab.ts to preserve cards across page reloads (opt-in).
 * 3. Resume unfinished clauses:
 *    - Identifies missing or failed clauses from the document clause list.
 *    - Calls POST /api/v1/clause-evaluations for unfinished/failed clauses only.
 *    - Reads streaming NDJSON events (progress, clause_result, clause_failed, done).
 *    - In case of network failure, preserves arrived cards and saves to sessionStorage if opted in.
 */

import { useEffect } from "react";
import type {
  TabClause,
  TabEvaluationCard,
  TabEvaluationState,
  TabEvaluationSummary,
} from "./keep-tab.ts";
import { saveTabResults } from "./keep-tab.ts";

export function getDefaultApiUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

export interface ProgressEvent {
  event: "progress";
  stage: string;
  clauses_done: number;
  clauses_total: number;
}

export interface ClauseResultEvent {
  event: "clause_result";
  clause: TabEvaluationCard;
}

export interface ClauseFailedEvent {
  event: "clause_failed";
  clause_id: string;
  error: string;
  status: "evaluation_failed" | "not_checked";
}

export interface DoneEvent {
  event: "done";
  summary: TabEvaluationSummary;
}

export type StreamEvaluationEvent =
  | ProgressEvent
  | ClauseResultEvent
  | ClauseFailedEvent
  | DoneEvent;

export interface ResumeOptions {
  state: TabEvaluationState;
  apiUrl?: string;
  fetchFn?: typeof fetch;
  customStorage?: Storage | null;
  onProgress?: (progress: ProgressEvent) => void;
  onClauseResult?: (card: TabEvaluationCard) => void;
  onClauseFailed?: (event: ClauseFailedEvent) => void;
  onDone?: (summary: TabEvaluationSummary) => void;
}

export interface ResumeResult {
  success: boolean;
  resumedCount: number;
  updatedState: TabEvaluationState;
  error?: string;
}

/**
 * Global beforeunload handler for accidental reload protection.
 */
export function beforeUnloadConfirmationHandler(event: BeforeUnloadEvent): string {
  event.preventDefault();
  // Standard browser prompt trigger
  event.returnValue = "";
  return "";
}

/**
 * Register the beforeunload confirmation listener.
 * Returns a cleanup function that unregisters the listener.
 */
export function enableBeforeUnloadProtection(): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  window.addEventListener("beforeunload", beforeUnloadConfirmationHandler);
  return () => {
    window.removeEventListener("beforeunload", beforeUnloadConfirmationHandler);
  };
}

/**
 * React hook to enable beforeunload protection when active (results or evaluation active).
 */
export function useRefreshProtection(isActive: boolean): void {
  useEffect(() => {
    if (!isActive) {
      return;
    }
    return enableBeforeUnloadProtection();
  }, [isActive]);
}

/**
 * Returns inline CSS properties to prevent accidental pull-to-refresh on mobile.
 */
export function getOverscrollContainmentStyle(): React.CSSProperties {
  return {
    overscrollBehaviorY: "contain",
  };
}

/**
 * Apply overscroll-behavior-y: contain to an HTML element (or document body if omitted).
 * Returns a cleanup function that restores the prior style.
 */
export function applyOverscrollContainment(targetElement?: HTMLElement | null): () => void {
  if (typeof document === "undefined") {
    return () => {};
  }
  const element = targetElement || document.body;
  if (!element) {
    return () => {};
  }
  const prevValue = element.style.overscrollBehaviorY;
  element.style.overscrollBehaviorY = "contain";
  return () => {
    element.style.overscrollBehaviorY = prevValue;
  };
}

/**
 * Calculate unfinished or failed clauses that need evaluation.
 */
export function getUnfinishedClauses(state: TabEvaluationState): TabClause[] {
  const cards = state.cards || {};
  const failedSet = new Set(state.failedClauseIds || []);

  return state.clauses.filter(
    (clause) => !cards[clause.clause_id] || failedSet.has(clause.clause_id)
  );
}

/**
 * Parse newline-delimited JSON chunks into individual events.
 */
export function parseNdjsonLines(buffer: string): {
  events: StreamEvaluationEvent[];
  remainingBuffer: string;
} {
  const lines = buffer.split("\n");
  const remainingBuffer = lines.pop() ?? "";
  const events: StreamEvaluationEvent[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    try {
      const parsed = JSON.parse(trimmed) as StreamEvaluationEvent;
      if (parsed && typeof parsed === "object" && "event" in parsed) {
        events.push(parsed);
      }
    } catch {
      // Ignore unparseable line fragments
    }
  }

  return { events, remainingBuffer };
}

/**
 * Resume evaluation of unfinished or failed clauses by calling POST /api/v1/clause-evaluations.
 *
 * Keeps all cards received so far. If the connection drops or an error occurs mid-evaluation,
 * preserves arrived cards and updates sessionStorage (if opted in).
 */
export async function resumeUnfinishedClauses(
  options: ResumeOptions
): Promise<ResumeResult> {
  const {
    state,
    apiUrl = getDefaultApiUrl(),
    fetchFn = typeof fetch !== "undefined" ? fetch : undefined,
    customStorage,
    onProgress,
    onClauseResult,
    onClauseFailed,
    onDone,
  } = options;

  if (!fetchFn) {
    return {
      success: false,
      resumedCount: 0,
      updatedState: state,
      error: "Fetch is not available in this environment.",
    };
  }

  const unfinishedClauses = getUnfinishedClauses(state);
  if (unfinishedClauses.length === 0) {
    return {
      success: true,
      resumedCount: 0,
      updatedState: state,
    };
  }

  // Clone state immutably to accumulate incoming cards
  const updatedCards = { ...state.cards };
  const failedSet = new Set(state.failedClauseIds);
  let updatedSummary = state.summary ?? null;
  let newlyResumed = 0;

  const currentUpdatedState = (): TabEvaluationState => ({
    ...state,
    cards: updatedCards,
    failedClauseIds: Array.from(failedSet),
    summary: updatedSummary,
  });

  try {
    const response = await fetchFn(`${apiUrl}/api/v1/clause-evaluations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        clauses: unfinishedClauses,
        contract_type: state.contractType,
      }),
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => "");
      // Preserve arrived cards in storage
      saveTabResults(currentUpdatedState(), customStorage);
      return {
        success: false,
        resumedCount: newlyResumed,
        updatedState: currentUpdatedState(),
        error: `HTTP error ${response.status}: ${errText}`,
      };
    }

    if (!response.body) {
      return {
        success: false,
        resumedCount: newlyResumed,
        updatedState: currentUpdatedState(),
        error: "Response body stream is not available.",
      };
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const processEvents = (events: StreamEvaluationEvent[]): void => {
      for (const ev of events) {
        if (ev.event === "progress") {
          onProgress?.(ev);
        } else if (ev.event === "clause_result") {
          updatedCards[ev.clause.clause_id] = ev.clause;
          failedSet.delete(ev.clause.clause_id);
          newlyResumed++;
          onClauseResult?.(ev.clause);
          // Progressively save arrived cards
          saveTabResults(currentUpdatedState(), customStorage);
        } else if (ev.event === "clause_failed") {
          failedSet.add(ev.clause_id);
          onClauseFailed?.(ev);
          saveTabResults(currentUpdatedState(), customStorage);
        } else if (ev.event === "done") {
          updatedSummary = ev.summary;
          onDone?.(ev.summary);
          saveTabResults(currentUpdatedState(), customStorage);
        }
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const { events, remainingBuffer } = parseNdjsonLines(buffer);
      buffer = remainingBuffer;
      processEvents(events);
    }

    // Process any trailing line in buffer
    if (buffer.trim()) {
      const { events } = parseNdjsonLines(buffer + "\n");
      processEvents(events);
    }

    const finalState = currentUpdatedState();
    saveTabResults(finalState, customStorage);

    return {
      success: true,
      resumedCount: newlyResumed,
      updatedState: finalState,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    // Keep arrived cards and save to storage on dropped stream
    const finalState = currentUpdatedState();
    saveTabResults(finalState, customStorage);

    return {
      success: false,
      resumedCount: newlyResumed,
      updatedState: finalState,
      error: errorMessage,
    };
  }
}
