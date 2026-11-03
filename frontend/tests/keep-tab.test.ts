import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  KEEP_TAB_OPT_IN_KEY,
  KEEP_TAB_STORAGE_KEY,
  KEEP_TAB_TTL_MS,
  NOT_SAVED_MESSAGE,
  EXPIRED_MESSAGE,
  getKeepTabOptIn,
  setKeepTabOptIn,
  saveTabResults,
  restoreTabResults,
  clearTabResults,
} from "../src/lib/keep-tab.ts";
import type { TabEvaluationState } from "../src/lib/keep-tab.ts";

class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

describe("keep-tab (MB-26 sessionStorage management)", () => {
  let storage: Storage;

  const sampleState: TabEvaluationState = {
    contractType: "recording",
    clauses: [
      {
        clause_id: "1.1",
        text: "Producer pays 16% of Net Receipts.",
        pages: [1],
        title: "Royalties",
      },
    ],
    cards: {
      "1.1": {
        clause_id: "1.1",
        status: "evaluated",
        comparison: "matches_standard",
        label: "typical",
        headline: "Streaming Royalties",
        what_it_says: "You receive 16% of net receipts.",
        what_it_means: "This affects your earnings.",
        comparison_note: "Matches reviewed standard.",
        pages: [1],
        original_text: "Producer pays 16% of Net Receipts.",
      },
    },
    failedClauseIds: [],
    summary: null,
  };

  beforeEach(() => {
    storage = new MemoryStorage();
  });

  it("defaults opt-in to false (off by default)", () => {
    assert.equal(getKeepTabOptIn(storage), false);
    assert.equal(storage.getItem(KEEP_TAB_OPT_IN_KEY), null);
  });

  it("stores opt-in when explicitly enabled", () => {
    setKeepTabOptIn(true, storage);
    assert.equal(getKeepTabOptIn(storage), true);
    assert.equal(storage.getItem(KEEP_TAB_OPT_IN_KEY), "true");
  });

  it("clears opt-in and clears saved results when disabled", () => {
    setKeepTabOptIn(true, storage);
    saveTabResults(sampleState, storage);
    assert.notEqual(storage.getItem(KEEP_TAB_STORAGE_KEY), null);

    // Disable opt-in
    setKeepTabOptIn(false, storage);
    assert.equal(getKeepTabOptIn(storage), false);
    assert.equal(storage.getItem(KEEP_TAB_OPT_IN_KEY), null);
    assert.equal(storage.getItem(KEEP_TAB_STORAGE_KEY), null);
  });

  it("does not save results if opt-in is disabled (no-op)", () => {
    const saved = saveTabResults(sampleState, storage);
    assert.equal(saved, false);
    assert.equal(storage.getItem(KEEP_TAB_STORAGE_KEY), null);
  });

  it("saves results when opt-in is enabled", () => {
    setKeepTabOptIn(true, storage);
    const now = 1700000000000;
    const saved = saveTabResults(sampleState, storage, now);

    assert.equal(saved, true);
    const storedRaw = storage.getItem(KEEP_TAB_STORAGE_KEY);
    assert.ok(storedRaw);

    const parsed = JSON.parse(storedRaw);
    assert.equal(parsed.savedAt, now);
    assert.deepEqual(parsed.data, sampleState);
  });

  it("returns explanatory not-saved message when restored without opt-in", () => {
    const result = restoreTabResults(Date.now(), storage);

    assert.equal(result.saved, false);
    assert.equal(result.optedIn, false);
    assert.equal(result.data, null);
    assert.equal(result.message, NOT_SAVED_MESSAGE);
  });

  it("restores valid data when opted in and within 60-minute TTL", () => {
    setKeepTabOptIn(true, storage);
    const savedTime = 1700000000000;
    saveTabResults(sampleState, storage, savedTime);

    // 30 minutes later (well within 60 min TTL)
    const restoreTime = savedTime + 30 * 60 * 1000;
    const result = restoreTabResults(restoreTime, storage);

    assert.equal(result.saved, true);
    assert.equal(result.optedIn, true);
    assert.equal(result.expired, false);
    assert.deepEqual(result.data, sampleState);
    assert.equal(result.message, null);
  });

  it("automatically expires and clears data after 60 minutes", () => {
    setKeepTabOptIn(true, storage);
    const savedTime = 1700000000000;
    saveTabResults(sampleState, storage, savedTime);

    // 61 minutes later (exceeds KEEP_TAB_TTL_MS)
    const expiredTime = savedTime + KEEP_TAB_TTL_MS + 1000;
    const result = restoreTabResults(expiredTime, storage);

    assert.equal(result.saved, false);
    assert.equal(result.optedIn, true);
    assert.equal(result.expired, true);
    assert.equal(result.data, null);
    assert.equal(result.message, EXPIRED_MESSAGE);

    // Confirm data was cleared from storage
    assert.equal(storage.getItem(KEEP_TAB_STORAGE_KEY), null);
  });

  it("explicitly clears saved results upon clearTabResults()", () => {
    setKeepTabOptIn(true, storage);
    saveTabResults(sampleState, storage);
    assert.ok(storage.getItem(KEEP_TAB_STORAGE_KEY));

    clearTabResults(storage);
    assert.equal(storage.getItem(KEEP_TAB_STORAGE_KEY), null);

    const result = restoreTabResults(Date.now(), storage);
    assert.equal(result.saved, false);
    assert.equal(result.optedIn, true);
    assert.equal(result.data, null);
  });
});
