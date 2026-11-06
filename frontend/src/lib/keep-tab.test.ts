import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EvaluationEvent } from "./api/stream";
import {
  KEEP_FOR_MS,
  clearKeptResults,
  forgetResults,
  keepResults,
  markResultsShown,
  restoreResults,
  resultsWereShown,
} from "./keep-tab";

const documentEvent: EvaluationEvent = {
  type: "document",
  schema_version: "1",
  payload: {
    page_count: 1,
    sections: [{ section_id: "main", title: null, kind: "body" }],
    clauses: [
      {
        clause_id: "1",
        section_id: "main",
        number: "1",
        heading: "Royalties",
        text: "Synthetic clause: the Artist receives 10% of net receipts.",
        pages: [1],
        start: 0,
        end: 58,
      },
    ],
    skipped_pages: [],
  },
};

const startedAt = Date.UTC(2026, 0, 1, 12);

function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => void items.delete(key),
    setItem: (key, value) => void items.set(key, String(value)),
  };
}

let storage: Storage;

beforeEach(() => {
  storage = memoryStorage();
  vi.stubGlobal("window", { sessionStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("keep-tab", () => {
  it("keeps nothing until asked", () => {
    expect(storage.length).toBe(0);
    expect(restoreResults(startedAt)).toBeNull();
  });

  it("restores kept results within the hour", () => {
    expect(keepResults({ keptSince: startedAt, events: [documentEvent] })).toBe(true);
    expect(restoreResults(startedAt + KEEP_FOR_MS - 1)).toEqual({
      keptSince: startedAt,
      events: [documentEvent],
    });
  });

  it("expires and clears kept results after 60 minutes", () => {
    keepResults({ keptSince: startedAt, events: [documentEvent] });
    expect(restoreResults(startedAt + KEEP_FOR_MS)).toBeNull();
    expect(storage.length).toBe(0);
  });

  it("clears on Clear now", () => {
    keepResults({ keptSince: startedAt, events: [documentEvent] });
    clearKeptResults();
    expect(storage.length).toBe(0);
    expect(restoreResults(startedAt)).toBeNull();
  });

  it("clears anything that doesn't match the contract", () => {
    storage.setItem("mbiu:kept-results", JSON.stringify({ keptSince: startedAt, events: [{}] }));
    expect(restoreResults(startedAt)).toBeNull();
    expect(storage.length).toBe(0);

    storage.setItem("mbiu:kept-results", "not json");
    expect(restoreResults(startedAt)).toBeNull();
    expect(storage.length).toBe(0);
  });

  it("reports when the browser won't store results", () => {
    storage.setItem = () => {
      throw new DOMException("Full", "QuotaExceededError");
    };
    expect(keepResults({ keptSince: startedAt, events: [documentEvent] })).toBe(false);
  });

  it("remembers only that results were shown, then forgets everything", () => {
    markResultsShown();
    expect(resultsWereShown()).toBe(true);
    expect(storage.getItem("mbiu:results-shown")).toBe("1");

    keepResults({ keptSince: startedAt, events: [documentEvent] });
    forgetResults();
    expect(resultsWereShown()).toBe(false);
    expect(storage.length).toBe(0);
  });

  it("does nothing without sessionStorage", () => {
    vi.stubGlobal("window", undefined);
    expect(keepResults({ keptSince: startedAt, events: [documentEvent] })).toBe(false);
    expect(restoreResults(startedAt)).toBeNull();
    expect(resultsWereShown()).toBe(false);
  });
});
