import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  beforeUnloadConfirmationHandler,
  getOverscrollContainmentStyle,
  getUnfinishedClauses,
  parseNdjsonLines,
  resumeUnfinishedClauses,
} from "../src/lib/refresh-protection.ts";
import type {
  TabClause,
  TabEvaluationCard,
  TabEvaluationState,
} from "../src/lib/keep-tab.ts";
import {
  setKeepTabOptIn,
  restoreTabResults,
} from "../src/lib/keep-tab.ts";

class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(key: string): string | null { return this.store.get(key) ?? null; }
  key(index: number): string | null { return Array.from(this.store.keys())[index] ?? null; }
  removeItem(key: string): void { this.store.delete(key); }
  setItem(key: string, value: string): void { this.store.set(key, String(value)); }
}

describe("refresh-protection (MB-26)", () => {
  it("beforeunload handler prevents default and sets returnValue", () => {
    let prevented = false;
    const mockEvent = {
      preventDefault: () => {
        prevented = true;
      },
      returnValue: "initial",
    } as unknown as BeforeUnloadEvent;

    const result = beforeUnloadConfirmationHandler(mockEvent);

    assert.equal(prevented, true);
    assert.equal(mockEvent.returnValue, "");
    assert.equal(result, "");
  });

  it("getOverscrollContainmentStyle returns overscroll-behavior-y contain", () => {
    const style = getOverscrollContainmentStyle();
    assert.deepEqual(style, { overscrollBehaviorY: "contain" });
  });

  it("getUnfinishedClauses filters evaluated cards and includes missing/failed clauses", () => {
    const clauses: TabClause[] = [
      { clause_id: "1", text: "Clause 1", pages: [1] },
      { clause_id: "2", text: "Clause 2", pages: [1] },
      { clause_id: "3", text: "Clause 3", pages: [2] },
    ];

    const cards: Record<string, TabEvaluationCard> = {
      "1": {
        clause_id: "1",
        status: "evaluated",
        comparison: "matches_standard",
        label: "typical",
        headline: "Topic 1",
        what_it_says: "Says 1",
        what_it_means: "Means 1",
        comparison_note: "Note 1",
        pages: [1],
        original_text: "Clause 1",
      },
      "2": {
        clause_id: "2",
        status: "evaluation_failed",
        comparison: "cannot_compare",
        label: "cannot_compare",
        headline: "Topic 2",
        what_it_says: "Says 2",
        what_it_means: "Means 2",
        comparison_note: "Note 2",
        pages: [1],
        original_text: "Clause 2",
      },
    };

    const state: TabEvaluationState = {
      clauses,
      cards,
      failedClauseIds: ["2"], // Clause 2 failed
      summary: null,
    };

    const unfinished = getUnfinishedClauses(state);

    // Clause 1 is evaluated and not failed -> excluded
    // Clause 2 is in failedClauseIds -> included
    // Clause 3 has no card in cards -> included
    assert.equal(unfinished.length, 2);
    const unfinishedIds = unfinished.map((c) => c.clause_id);
    assert.deepEqual(unfinishedIds, ["2", "3"]);
  });

  it("parseNdjsonLines splits buffer into events and preserves trailing line fragment", () => {
    const buffer =
      '{"event":"progress","stage":"evaluating","clauses_done":0,"clauses_total":2}\n' +
      '{"event":"clause_result","clause":{"clause_id":"1","status":"evaluated"}}\n' +
      '{"event":"prog';

    const { events, remainingBuffer } = parseNdjsonLines(buffer);

    assert.equal(events.length, 2);
    assert.equal(events[0].event, "progress");
    assert.equal(events[1].event, "clause_result");
    assert.equal(remainingBuffer, '{"event":"prog');
  });

  it("resumeUnfinishedClauses returns immediately when all clauses are completed", async () => {
    let fetchCalled = false;
    const mockFetch = async () => {
      fetchCalled = true;
      return new Response("");
    };

    const state: TabEvaluationState = {
      clauses: [{ clause_id: "1", text: "Text", pages: [1] }],
      cards: {
        "1": {
          clause_id: "1",
          status: "evaluated",
          comparison: "matches_standard",
          label: "typical",
          headline: "H",
          what_it_says: "S",
          what_it_means: "M",
          comparison_note: "N",
          pages: [1],
          original_text: "Text",
        },
      },
      failedClauseIds: [],
    };

    const result = await resumeUnfinishedClauses({
      state,
      fetchFn: mockFetch as unknown as typeof fetch,
    });

    assert.equal(result.success, true);
    assert.equal(result.resumedCount, 0);
    assert.equal(fetchCalled, false);
  });

  it("resumeUnfinishedClauses requests only unfinished clauses and streams events", async () => {
    const clauses: TabClause[] = [
      { clause_id: "1", text: "Done clause", pages: [1] },
      { clause_id: "2", text: "Unfinished clause", pages: [2] },
    ];

    const existingCard: TabEvaluationCard = {
      clause_id: "1",
      status: "evaluated",
      comparison: "matches_standard",
      label: "typical",
      headline: "Done Headline",
      what_it_says: "Says",
      what_it_means: "Means",
      comparison_note: "Note",
      pages: [1],
      original_text: "Done clause",
    };

    const resumedCard: TabEvaluationCard = {
      clause_id: "2",
      status: "evaluated",
      comparison: "matches_standard",
      label: "typical",
      headline: "Resumed Headline",
      what_it_says: "Resumed Says",
      what_it_means: "Resumed Means",
      comparison_note: "Resumed Note",
      pages: [2],
      original_text: "Unfinished clause",
    };

    let sentBody: string | null = null;
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({
              event: "progress",
              stage: "evaluating",
              clauses_done: 1,
              clauses_total: 1,
            }) + "\n"
          )
        );
        controller.enqueue(
          encoder.encode(
            JSON.stringify({
              event: "clause_result",
              clause: resumedCard,
            }) + "\n"
          )
        );
        controller.enqueue(
          encoder.encode(
            JSON.stringify({
              event: "done",
              summary: { top_asks: ["Ask 1?"] },
            }) + "\n"
          )
        );
        controller.close();
      },
    });

    const mockFetch = async (
      _input: RequestInfo | URL,
      init?: RequestInit
    ): Promise<Response> => {
      sentBody = (init?.body as string) || null;
      return new Response(stream, {
        status: 200,
        headers: { "Content-Type": "application/x-ndjson" },
      });
    };

    const storage = new MemoryStorage();
    setKeepTabOptIn(true, storage);

    const initialState: TabEvaluationState = {
      contractType: "recording",
      clauses,
      cards: { "1": existingCard },
      failedClauseIds: [],
    };

    const result = await resumeUnfinishedClauses({
      state: initialState,
      fetchFn: mockFetch as unknown as typeof fetch,
      customStorage: storage,
    });

    assert.equal(result.success, true);
    assert.equal(result.resumedCount, 1);
    assert.ok(result.updatedState.cards["1"]);
    assert.ok(result.updatedState.cards["2"]);
    assert.equal(result.updatedState.cards["2"].headline, "Resumed Headline");

    // Verify only unfinished clause 2 was sent to server
    assert.ok(sentBody);
    const parsedBody = JSON.parse(sentBody);
    assert.equal(parsedBody.clauses.length, 1);
    assert.equal(parsedBody.clauses[0].clause_id, "2");

    // Verify state was saved to sessionStorage
    const restored = restoreTabResults(Date.now(), storage);
    assert.equal(restored.saved, true);
    assert.ok(restored.data?.cards["2"]);
  });

  it("resumeUnfinishedClauses preserves arrived cards on network drop", async () => {
    const clauses: TabClause[] = [
      { clause_id: "1", text: "Text 1", pages: [1] },
      { clause_id: "2", text: "Text 2", pages: [2] },
    ];

    const encoder = new TextEncoder();
    let sentFirstChunk = false;
    const stream = new ReadableStream({
      pull(controller) {
        if (!sentFirstChunk) {
          sentFirstChunk = true;
          controller.enqueue(
            encoder.encode(
              JSON.stringify({
                event: "clause_result",
                clause: {
                  clause_id: "1",
                  status: "evaluated",
                  comparison: "matches_standard",
                  label: "typical",
                  headline: "Card 1",
                  what_it_says: "Says 1",
                  what_it_means: "Means 1",
                  comparison_note: "Note 1",
                  pages: [1],
                  original_text: "Text 1",
                },
              }) + "\n"
            )
          );
        } else {
          // Simulate network drop mid-stream
          controller.error(new Error("Connection reset by peer"));
        }
      },
    });

    const mockFetch = async (): Promise<Response> => {
      return new Response(stream, { status: 200 });
    };

    const storage = new MemoryStorage();
    setKeepTabOptIn(true, storage);

    const initialState: TabEvaluationState = {
      clauses,
      cards: {},
      failedClauseIds: [],
    };

    const result = await resumeUnfinishedClauses({
      state: initialState,
      fetchFn: mockFetch as unknown as typeof fetch,
      customStorage: storage,
    });

    assert.equal(result.success, false);
    assert.ok(result.error?.includes("Connection reset by peer"));
    // Card 1 arrived before stream drop and was preserved
    assert.ok(result.updatedState.cards["1"]);
    assert.equal(result.updatedState.cards["1"].headline, "Card 1");

    // Card 1 also persisted in storage
    const restored = restoreTabResults(Date.now(), storage);
    assert.equal(restored.saved, true);
    assert.ok(restored.data?.cards["1"]);
  });
});
