import type { Clause } from "./api/generated/types.gen";
import type { EvaluationEvent } from "./api/stream";

/**
 * The events behind the results on screen: the latest of each kind, and the latest per
 * clause. Replaying it rebuilds the results, and it shows which clauses are unfinished.
 */
export type ResultsLog = ReadonlyMap<string, EvaluationEvent>;

export const emptyLog: ResultsLog = new Map();

function keyOf(event: EvaluationEvent): string | null {
  switch (event.type) {
    case "progress":
      return null;
    case "clause_result":
    case "clause_updated":
    case "clause_failed":
      return `clause:${event.payload.clause_id}`;
    default:
      return event.type;
  }
}

export function withEvent(log: ResultsLog, event: EvaluationEvent): ResultsLog {
  const key = keyOf(event);
  return key === null ? log : new Map(log).set(key, event);
}

/**
 * Clauses still worth checking: no result yet, a retryable failure, or not checked
 * before the time budget ran out.
 */
export function unfinishedClauses(log: ResultsLog): Clause[] {
  const document = log.get("document");
  if (document?.type !== "document") return [];
  return document.payload.clauses.filter((clause) => {
    const event = log.get(`clause:${clause.clause_id}`);
    if (event?.type === "clause_failed") return event.payload.retryable;
    if (event?.type === "clause_result" || event?.type === "clause_updated") {
      return event.payload.status === "not_checked";
    }
    return true;
  });
}

export async function* replay(events: Iterable<EvaluationEvent>) {
  yield* events;
}

/**
 * Passes a stream through, reporting each event, then whether the stream ended
 * cleanly and whether it sent its final summary.
 */
export async function* tracked(
  source: AsyncIterable<EvaluationEvent>,
  onEvent: (event: EvaluationEvent) => void,
  onEnd: (end: { complete: boolean; sawDone: boolean }) => void
) {
  let complete = false;
  let sawDone = false;
  try {
    for await (const event of source) {
      sawDone ||= event.type === "done";
      onEvent(event);
      yield event;
    }
    complete = true;
  } finally {
    onEnd({ complete, sawDone });
  }
}
