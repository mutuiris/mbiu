import { z } from "zod";

import { zStreamEvent } from "./api/generated/zod.gen";
import type { EvaluationEvent } from "./api/stream";

/**
 * Keeps results for this tab only, and only when the artist turns it on. The browser
 * clears sessionStorage when the tab closes; we also clear it after an hour, on
 * "Clear now", and when the artist checks another contract.
 */

const KEPT_KEY = "mbiu:kept-results";
// Holds "1" and nothing else, so a reload can say the results weren't kept
const SHOWN_KEY = "mbiu:results-shown";

export const KEEP_FOR_MS = 60 * 60 * 1000;

export const NOT_SAVED_MESSAGE =
  "Your results weren't saved on this device. Upload the contract again to see them.";

export interface KeptResults {
  /** When the artist turned keeping on; the hour counts from here. */
  keptSince: number;
  events: EvaluationEvent[];
}

const zKeptResults = z.object({ keptSince: z.number(), events: z.array(zStreamEvent) });

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

/** Returns false when the browser won't store them, for example when it's full. */
export function keepResults(kept: KeptResults): boolean {
  const store = storage();
  if (!store) return false;
  try {
    store.setItem(KEPT_KEY, JSON.stringify(kept));
    return true;
  } catch {
    store.removeItem(KEPT_KEY);
    return false;
  }
}

/** This tab's kept results, or null when there are none, they expired or they don't parse. */
export function restoreResults(now = Date.now()): KeptResults | null {
  const raw = storage()?.getItem(KEPT_KEY);
  if (!raw) return null;
  try {
    const kept = zKeptResults.parse(JSON.parse(raw));
    if (now - kept.keptSince < KEEP_FOR_MS) {
      return {
        keptSince: kept.keptSince,
        events: kept.events.filter((event) => event.type !== "heartbeat"),
      };
    }
  } catch {
    // Unreadable, so it is cleared below
  }
  clearKeptResults();
  return null;
}

export function clearKeptResults(): void {
  storage()?.removeItem(KEPT_KEY);
}

export function markResultsShown(): void {
  try {
    storage()?.setItem(SHOWN_KEY, "1");
  } catch {
    // Only costs the "weren't saved" message after a reload
  }
}

export function resultsWereShown(): boolean {
  return storage()?.getItem(SHOWN_KEY) === "1";
}

/** Clears everything this tab holds. */
export function forgetResults(): void {
  clearKeptResults();
  storage()?.removeItem(SHOWN_KEY);
}
