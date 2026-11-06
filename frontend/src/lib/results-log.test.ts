import { describe, expect, it } from "vitest";

import type { Clause, ClauseResult } from "./api/generated/types.gen";
import type { EvaluationEvent } from "./api/stream";
import { emptyLog, replay, tracked, unfinishedClauses, withEvent } from "./results-log";

function clause(id: string): Clause {
  const text = `Synthetic clause ${id}.`;
  return {
    clause_id: id,
    section_id: "main",
    number: id,
    heading: null,
    text,
    pages: [1],
    start: 0,
    end: text.length,
  };
}

function result(id: string, status: ClauseResult["status"]): EvaluationEvent {
  return {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: id,
      pages: [1],
      original_text: `Synthetic clause ${id}.`,
      status,
      comparison: "cannot_compare",
      headline: "Synthetic headline",
      what_it_says: "Synthetic summary.",
      what_it_means: "Synthetic meaning.",
      comparison_note: null,
      impact_inputs: null,
      linked_clauses: [],
      fairer_wording: null,
      ask_them: null,
      standard_template_id: null,
      standard_excerpt: null,
      evidence: [],
      evidence_ids: [],
      evidence_quote: null,
      provider: null,
      model_version: null,
    },
  };
}

function failed(id: string, retryable: boolean): EvaluationEvent {
  return {
    type: "clause_failed",
    schema_version: "1",
    payload: { clause_id: id, reason: retryable ? "timeout" : "refused", retryable },
  };
}

const documentEvent: EvaluationEvent = {
  type: "document",
  schema_version: "1",
  payload: {
    page_count: 1,
    sections: [{ section_id: "main", title: null, kind: "body" }],
    clauses: ["1", "2", "3", "4", "5"].map(clause),
    skipped_pages: [],
  },
};

const progress: EvaluationEvent = {
  type: "progress",
  schema_version: "1",
  payload: { stage: "compare", done: 1, total: 5 },
};

function logOf(events: EvaluationEvent[]) {
  return events.reduce(withEvent, emptyLog);
}

describe("results log", () => {
  it("keeps the latest event per clause and drops progress", () => {
    const log = logOf([documentEvent, progress, failed("1", true), result("1", "evaluated")]);
    expect([...log.values()]).toEqual([documentEvent, result("1", "evaluated")]);
  });

  it("finds clauses with no result, a retryable failure, or not checked in time", () => {
    const log = logOf([
      documentEvent,
      result("1", "evaluated"),
      result("2", "not_checked"),
      failed("3", true),
      failed("4", false),
    ]);
    expect(unfinishedClauses(log).map((c) => c.clause_id)).toEqual(["2", "3", "5"]);
  });

  it("has nothing to resume before the document arrives", () => {
    expect(unfinishedClauses(logOf([result("1", "evaluated")]))).toEqual([]);
  });

  it("reports a stream that ends cleanly", async () => {
    const seen: EvaluationEvent[] = [];
    let end: unknown;
    for await (const event of tracked(
      replay([documentEvent, progress]),
      (e) => seen.push(e),
      (e) => (end = e)
    )) {
      expect(event).toBeDefined();
    }
    expect(seen).toEqual([documentEvent, progress]);
    expect(end).toEqual({ complete: true, sawDone: false });
  });

  it("reports a stream that drops, keeping what arrived", async () => {
    async function* dropping() {
      yield documentEvent;
      throw new TypeError("network error");
    }
    const seen: EvaluationEvent[] = [];
    let end: unknown;
    await expect(async () => {
      for await (const event of tracked(dropping(), (e) => seen.push(e), (e) => (end = e))) {
        expect(event).toBeDefined();
      }
    }).rejects.toThrow("network error");
    expect(seen).toEqual([documentEvent]);
    expect(end).toEqual({ complete: false, sawDone: false });
  });
});
