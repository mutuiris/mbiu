/**
 * Tab-only sessionStorage management for contract evaluation results (MB-26).
 *
 * Invariants & Policies:
 * - Explicit opt-in toggle, off by default:
 *   "Keep my results if this page reloads. Leave this off on a shared phone."
 * - Tab-only sessionStorage: results are cleared automatically when the tab closes.
 * - 60-minute TTL: data older than 60 minutes automatically expires and clears.
 * - Explicit clearing: cleared upon calling clearTabResults().
 * - When restored without opt-in: returns state indicating
 *   "Your results weren't saved on this device. Upload the contract again to see them."
 * - Zero Server Storage: nothing is ever stored on the server or in persistent device cookies/localStorage.
 */

export const KEEP_TAB_OPT_IN_KEY = "mbiu_keep_tab_opt_in";
export const KEEP_TAB_STORAGE_KEY = "mbiu_tab_results_v1";
export const KEEP_TAB_TTL_MS = 60 * 60 * 1000; // 60 minutes

export const OPT_IN_NOTICE_TEXT =
  "Keep my results if this page reloads. Leave this off on a shared phone.";

export const NOT_SAVED_MESSAGE =
  "Your results weren't saved on this device. Upload the contract again to see them.";

export const EXPIRED_MESSAGE =
  "Saved results expired after 60 minutes. Upload the contract again to see them.";

export interface TabClause {
  clause_id: string;
  text: string;
  pages: number[];
  title?: string | null;
  section?: string | null;
}

export type ResultLabel =
  | "typical"
  | "unusual"
  | "worth_asking_about"
  | "cannot_compare";

export interface TabEvaluationCard {
  clause_id: string;
  status: string;
  comparison: string;
  label: ResultLabel;
  headline: string;
  what_it_says: string;
  what_it_means: string;
  comparison_note: string;
  pages: number[];
  original_text: string;
  ask_them?: string[];
  fairer_wording?: string | null;
  impact_inputs?: {
    rate?: string | number | null;
    basis?: string | null;
    deductions?: string[];
    quote?: string | null;
  } | null;
  [key: string]: unknown;
}

export interface TabEvaluationSummary {
  top_asks: string[];
  contract_issues?: unknown[];
  missing_protections?: unknown[];
  good_news?: unknown[];
  matches_count?: number;
  skipped_pages?: number[];
  ask_list?: string[];
  clauses_not_checked?: number;
  label_counts?: Record<string, number>;
  versions?: {
    schema_version?: string;
    prompt_version?: string;
    model_version?: string;
    corpus_version?: string;
  };
  [key: string]: unknown;
}

export interface TabEvaluationState {
  contractType?: string | null;
  clauses: TabClause[];
  cards: Record<string, TabEvaluationCard>;
  failedClauseIds: string[];
  summary?: TabEvaluationSummary | null;
  chat?: Array<{
    role: string;
    message: string;
    timestamp?: number;
  }>;
}

interface StoredPayload {
  savedAt: number;
  data: TabEvaluationState;
}

export interface TabRestoreResult {
  saved: boolean;
  optedIn: boolean;
  expired?: boolean;
  data: TabEvaluationState | null;
  message: string | null;
}

/**
 * Resolve sessionStorage safely, returning null in non-browser or SSR contexts.
 */
function resolveStorage(customStorage?: Storage | null): Storage | null {
  if (customStorage !== undefined) {
    return customStorage;
  }
  if (typeof window !== "undefined" && typeof window.sessionStorage !== "undefined") {
    return window.sessionStorage;
  }
  return null;
}

/**
 * Check whether the user has explicitly opted into keeping tab results.
 * Defaults to false (off by default).
 */
export function getKeepTabOptIn(customStorage?: Storage | null): boolean {
  const storage = resolveStorage(customStorage);
  if (!storage) {
    return false;
  }
  try {
    return storage.getItem(KEEP_TAB_OPT_IN_KEY) === "true";
  } catch {
    return false;
  }
}

/**
 * Set user opt-in status. When turned off, clears any currently held tab results.
 */
export function setKeepTabOptIn(
  enabled: boolean,
  customStorage?: Storage | null
): void {
  const storage = resolveStorage(customStorage);
  if (!storage) {
    return;
  }
  try {
    if (enabled) {
      storage.setItem(KEEP_TAB_OPT_IN_KEY, "true");
    } else {
      storage.removeItem(KEEP_TAB_OPT_IN_KEY);
      clearTabResults(storage);
    }
  } catch {
    // Graceful fallback if storage quota exceeded or disabled
  }
}

/**
 * Save evaluation state to sessionStorage for this tab only.
 * Only executes if opt-in is enabled. Returns true if saved, false otherwise.
 */
export function saveTabResults(
  data: TabEvaluationState,
  customStorage?: Storage | null,
  now = Date.now()
): boolean {
  const storage = resolveStorage(customStorage);
  if (!storage) {
    return false;
  }
  if (!getKeepTabOptIn(storage)) {
    return false;
  }
  try {
    const payload: StoredPayload = {
      savedAt: now,
      data,
    };
    storage.setItem(KEEP_TAB_STORAGE_KEY, JSON.stringify(payload));
    return true;
  } catch {
    return false;
  }
}

/**
 * Restore results from sessionStorage.
 *
 * Rules:
 * - If user did not opt in, returns message:
 *   "Your results weren't saved on this device. Upload the contract again to see them."
 * - If data is older than 60 minutes, automatically expires, clears, and returns expired message.
 * - If valid data exists within 60 minutes, restores it cleanly.
 */
export function restoreTabResults(
  now = Date.now(),
  customStorage?: Storage | null
): TabRestoreResult {
  const storage = resolveStorage(customStorage);
  if (!storage) {
    return {
      saved: false,
      optedIn: false,
      data: null,
      message: NOT_SAVED_MESSAGE,
    };
  }

  const optedIn = getKeepTabOptIn(storage);
  if (!optedIn) {
    return {
      saved: false,
      optedIn: false,
      data: null,
      message: NOT_SAVED_MESSAGE,
    };
  }

  try {
    const raw = storage.getItem(KEEP_TAB_STORAGE_KEY);
    if (!raw) {
      return {
        saved: false,
        optedIn: true,
        data: null,
        message: null,
      };
    }

    const payload: StoredPayload = JSON.parse(raw);
    const age = now - payload.savedAt;

    if (age > KEEP_TAB_TTL_MS) {
      clearTabResults(storage);
      return {
        saved: false,
        optedIn: true,
        expired: true,
        data: null,
        message: EXPIRED_MESSAGE,
      };
    }

    return {
      saved: true,
      optedIn: true,
      expired: false,
      data: payload.data,
      message: null,
    };
  } catch {
    clearTabResults(storage);
    return {
      saved: false,
      optedIn: true,
      data: null,
      message: null,
    };
  }
}

/**
 * Explicitly clear tab results from sessionStorage.
 */
export function clearTabResults(customStorage?: Storage | null): void {
  const storage = resolveStorage(customStorage);
  if (!storage) {
    return;
  }
  try {
    storage.removeItem(KEEP_TAB_STORAGE_KEY);
  } catch {
    // Graceful no-op
  }
}
