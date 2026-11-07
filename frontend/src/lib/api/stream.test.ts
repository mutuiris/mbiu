import { describe, expect, it, vi } from "vitest";
import {
  parseNDJSONStream,
  generateTraceparent,
  getImpactRank,
  sortByImpactOrder,
  StreamParseError,
  StreamValidationError,
  fetchEvaluationStream,
  fetchClauseEvaluations,
  ApiStreamError,
  ServiceUnavailableError,
} from "./stream";
import type { Clause, ClauseResult } from "./generated/types.gen";

function createStreamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

const mockDocEvent = {
  type: "document",
  schema_version: "1",
  payload: {
    page_count: 1,
    sections: [{ section_id: "sec-1", title: "Main", kind: "body" }],
    clauses: [
      {
        clause_id: "c1",
        section_id: "sec-1",
        number: "1.0",
        heading: "Grant",
        pages: [1],
        start: 0,
        end: 50,
        text: "Sample clause text",
      },
    ],
    skipped_pages: [],
  },
};

const mockHeartbeatEvent = {
  type: "heartbeat",
  schema_version: "1",
  payload: {},
};

const mockProgressEvent = {
  type: "progress",
  schema_version: "1",
  payload: {
    stage: "compare",
    done: 1,
    total: 2,
  },
};

const mockClauseResultEvent = {
  type: "clause_result",
  schema_version: "1",
  payload: {
    clause_id: "c1",
    status: "evaluated",
    comparison: "worse_for_you",
    headline: "You lose your rights forever",
    what_it_says: "Assignment in perpetuity",
    what_it_means: "Never reverts back to you",
    original_text: "Sample clause text",
    pages: [1],
    linked_clauses: [],
    evidence: [],
    evidence_ids: [],
    comparison_note: null,
    evidence_quote: null,
    standard_excerpt: null,
    standard_template_id: null,
    ask_them: "Can we do a license instead?",
    impact_inputs: null,
    provider: "gemini",
    model_version: "gemini-3.8-flash",
  },
};

describe("Stream Parsing (parseNDJSONStream)", () => {
  it("handles split chunks across stream reads", async () => {
    const jsonStr = JSON.stringify(mockDocEvent);
    // Split the JSON line right down the middle across two chunks
    const mid = Math.floor(jsonStr.length / 2);
    const chunk1 = jsonStr.slice(0, mid);
    const chunk2 = jsonStr.slice(mid) + "\n";

    const stream = createStreamFromChunks([chunk1, chunk2]);
    const events = [];

    for await (const event of parseNDJSONStream(stream)) {
      events.push(event);
    }

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe("document");
    expect((events[0] as typeof mockDocEvent).payload.page_count).toBe(1);
  });

  it("handles multiple events per chunk", async () => {
    const chunk = `${JSON.stringify(mockDocEvent)}\n${JSON.stringify(mockProgressEvent)}\n${JSON.stringify(mockClauseResultEvent)}\n`;
    const stream = createStreamFromChunks([chunk]);
    const events = [];

    for await (const event of parseNDJSONStream(stream)) {
      events.push(event);
    }

    expect(events).toHaveLength(3);
    expect(events[0].type).toBe("document");
    expect(events[1].type).toBe("progress");
    expect(events[2].type).toBe("clause_result");
  });

  it("ignores heartbeat events", async () => {
    const chunk = `${JSON.stringify(mockDocEvent)}\n${JSON.stringify(mockHeartbeatEvent)}\n${JSON.stringify(mockProgressEvent)}\n${JSON.stringify(mockHeartbeatEvent)}\n`;
    const stream = createStreamFromChunks([chunk]);
    const events = [];

    for await (const event of parseNDJSONStream(stream)) {
      events.push(event);
    }

    // Both heartbeats must be filtered out
    expect(events).toHaveLength(2);
    expect(events.map((e) => e.type)).toEqual(["document", "progress"]);
  });

  it("surfaces invalid JSON as StreamParseError", async () => {
    const brokenChunk = '{"type": "document", "schema_version": "1", "payload": {\n';
    const stream = createStreamFromChunks([brokenChunk]);

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _ of parseNDJSONStream(stream)) {
        // do nothing
      }
    }).rejects.toThrow(StreamParseError);
  });

  it("surfaces schema violations as StreamValidationError", async () => {
    // Valid JSON but fails Zod schema because required 'type' is missing or payload is invalid
    const invalidSchemaChunk = JSON.stringify({
      type: "clause_result",
      schema_version: "1",
      payload: {
        // missing required fields: clause_id, pages, what_it_says, etc.
        headline: "Missing fields",
      },
    }) + "\n";

    const stream = createStreamFromChunks([invalidSchemaChunk]);

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _ of parseNDJSONStream(stream)) {
        // do nothing
      }
    }).rejects.toThrow(StreamValidationError);
  });
});

describe("generateTraceparent", () => {
  it("generates a valid W3C traceparent header", () => {
    const traceparent = generateTraceparent();
    // Format: 00-{32 hex}-{16 hex}-01
    const regex = /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/;
    expect(traceparent).toMatch(regex);
  });

  it("generates unique trace IDs on successive calls", () => {
    const tp1 = generateTraceparent();
    const tp2 = generateTraceparent();
    expect(tp1).not.toBe(tp2);
  });
});

describe("Impact Ordering", () => {
  it("ranks outcomes with worse_for_you first and matches_standard last", () => {
    expect(getImpactRank("worse_for_you")).toBe(1);
    expect(getImpactRank("missing_from_contract")).toBe(2);
    expect(getImpactRank("not_in_standard")).toBe(3);
    expect(getImpactRank("cannot_compare")).toBe(4);
    expect(getImpactRank("better_for_you")).toBe(5);
    expect(getImpactRank("matches_standard")).toBe(6);
  });

  it("sorts clause cards in impact order", () => {
    const makeCard = (id: string, comparison: ClauseResult["comparison"], page: number): ClauseResult => ({
      clause_id: id,
      comparison,
      headline: `Headline ${id}`,
      status: "evaluated",
      what_it_says: "says",
      what_it_means: "means",
      original_text: "orig",
      pages: [page],
      linked_clauses: [],
      evidence: [],
      evidence_ids: [],
      comparison_note: null,
      evidence_quote: null,
      standard_excerpt: null,
      standard_template_id: null,
      ask_them: null,
      impact_inputs: null,
      provider: null,
      model_version: null,
    });

    const cardMatch = makeCard("c-match", "matches_standard", 1);
    const cardBetter = makeCard("c-better", "better_for_you", 2);
    const cardWorse = makeCard("c-worse", "worse_for_you", 3);
    const cardMissing = makeCard("c-missing", "missing_from_contract", 4);

    const sorted = sortByImpactOrder([cardMatch, cardBetter, cardWorse, cardMissing]);

    expect(sorted.map((c) => c.clause_id)).toEqual([
      "c-worse",
      "c-missing",
      "c-better",
      "c-match",
    ]);
  });
});

describe("fetchEvaluationStream error handling", () => {
  it("throws ServiceUnavailableError when API returns 503", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        code: "service_unavailable",
        message: "Mbiu can't check contracts right now.",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const file = new Blob(["mock pdf"], { type: "application/pdf" });

    await expect(
      fetchEvaluationStream({
        file,
        turnstileToken: "dummy-token",
        apiUrl: "http://localhost:8000",
      })
    ).rejects.toThrow(ServiceUnavailableError);

    vi.unstubAllGlobals();
  });
});

describe("fetchClauseEvaluations", () => {
  it("sends only the given clauses as JSON and streams the results", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: createStreamFromChunks([JSON.stringify(mockClauseResultEvent) + "\n"]),
    });
    vi.stubGlobal("fetch", mockFetch);
    const clauses = mockDocEvent.payload.clauses as Clause[];

    const events = [];
    for await (const event of await fetchClauseEvaluations({
      clauses,
      turnstileToken: "dummy-token",
      apiUrl: "http://localhost:8000/",
    })) {
      events.push(event);
    }

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/clause-evaluations");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ clauses, turnstile_token: "dummy-token" });
    expect(events).toEqual([mockClauseResultEvent]);

    vi.unstubAllGlobals();
  });

  it("surfaces a refused request as ApiStreamError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ code: "bot_check_failed", message: "Please try the check again." }),
      })
    );

    await expect(
      fetchClauseEvaluations({
        clauses: mockDocEvent.payload.clauses as Clause[],
        turnstileToken: "dummy-token",
      })
    ).rejects.toThrow(ApiStreamError);

    vi.unstubAllGlobals();
  });
});
