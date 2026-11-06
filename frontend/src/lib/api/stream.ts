import { zStreamEvent, zApiError } from "./generated/zod.gen";
import type {
  StreamEvent,
  ClauseResult,
  Outcome,
  ApiError,
} from "./generated/types.gen";

/**
 * All stream events except heartbeats, which are filtered out.
 */
export type EvaluationEvent = Exclude<StreamEvent, { type: "heartbeat" }>;

/**
 * Priority rank for sorting clause results in impact order.
 * 1 is highest impact (worse for artist), 6 is standard match (collapsed).
 */
export function getImpactRank(outcome: Outcome): number {
  switch (outcome) {
    case "worse_for_you":
      return 1;
    case "missing_from_contract":
      return 2;
    case "not_in_standard":
      return 3;
    case "cannot_compare":
      return 4;
    case "better_for_you":
      return 5;
    case "matches_standard":
      return 6;
    default:
      return 7;
  }
}

/**
 * Sort helper that sorts ClauseResults by impact order (highest risk first).
 */
export function sortByImpactOrder(cards: ClauseResult[]): ClauseResult[] {
  return [...cards].sort((a, b) => {
    const rankDiff = getImpactRank(a.comparison) - getImpactRank(b.comparison);
    if (rankDiff !== 0) return rankDiff;
    // Tie-breaker: preserve clause order by first page then clause_id
    const pageA = a.pages[0] ?? 0;
    const pageB = b.pages[0] ?? 0;
    if (pageA !== pageB) return pageA - pageB;
    return a.clause_id.localeCompare(b.clause_id);
  });
}

/**
 * Generate a random W3C traceparent header:
 * Format: 00-${traceId}-${spanId}-${flags}
 * - traceId: 16 bytes (32 hex characters, non-zero)
 * - spanId: 8 bytes (16 hex characters, non-zero)
 * - flags: 01 (sampled)
 */
export function generateTraceparent(): string {
  const bytes = new Uint8Array(24);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 24; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }

  // Ensure non-zero identifiers
  if (bytes[0] === 0) bytes[0] = 1;
  if (bytes[16] === 0) bytes[16] = 1;

  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  const traceId = hex.slice(0, 32);
  const spanId = hex.slice(32, 48);

  return `00-${traceId}-${spanId}-01`;
}

export class StreamParseError extends Error {
  constructor(
    message: string,
    public readonly rawLine: string,
    public readonly cause?: unknown
  ) {
    super(message);
    this.name = "StreamParseError";
  }
}

export class StreamValidationError extends Error {
  constructor(
    message: string,
    public readonly rawLine: string,
    public readonly issues?: unknown
  ) {
    super(message);
    this.name = "StreamValidationError";
  }
}

export class ServiceUnavailableError extends Error {
  constructor(
    message: string = "Mbiu can't check contracts right now. Your clauses are listed below; try again in a few minutes.",
    public readonly apiError?: ApiError
  ) {
    super(message);
    this.name = "ServiceUnavailableError";
  }
}

export class ApiStreamError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly apiError?: ApiError
  ) {
    super(message);
    this.name = "ApiStreamError";
  }
}

/**
 * Reads a ReadableStream emitting NDJSON (newline-delimited JSON), validates each
 * line with the generated Zod schemas, ignores heartbeats, and surfaces invalid lines as errors.
 */
export async function* parseNDJSONStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<EvaluationEvent, void, unknown> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // The last element is the uncompleted tail of the buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        let parsedJson: unknown;
        try {
          parsedJson = JSON.parse(trimmed);
        } catch (err) {
          throw new StreamParseError(
            "Failed to parse stream line as JSON",
            trimmed,
            err
          );
        }

        const result = zStreamEvent.safeParse(parsedJson);
        if (!result.success) {
          throw new StreamValidationError(
            `Stream event failed schema validation: ${result.error.message}`,
            trimmed,
            result.error.issues
          );
        }

        const event = result.data;
        // Ignore heartbeats
        if (event.type === "heartbeat") {
          continue;
        }

        yield event as EvaluationEvent;
      }
    }

    // Process any remaining data in the buffer after the stream ends
    const remainder = buffer.trim();
    if (remainder) {
      let parsedJson: unknown;
      try {
        parsedJson = JSON.parse(remainder);
      } catch (err) {
        throw new StreamParseError(
          "Failed to parse trailing stream line as JSON",
          remainder,
          err
        );
      }

      const result = zStreamEvent.safeParse(parsedJson);
      if (!result.success) {
        throw new StreamValidationError(
          `Trailing stream event failed schema validation: ${result.error.message}`,
          remainder,
          result.error.issues
        );
      }

      const event = result.data;
      if (event.type !== "heartbeat") {
        yield event as EvaluationEvent;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Shown before any clause has arrived, so it must not mention clauses below
const PRE_STREAM_UNAVAILABLE = "Mbiu can't check contracts right now. Please try again in a few minutes.";

export interface FetchEvaluationOptions {
  file: File | Blob;
  turnstileToken: string;
  apiUrl?: string;
  traceparent?: string;
  signal?: AbortSignal;
}

/**
 * Posts the contract file and turnstile token to /api/v1/evaluations and returns
 * an async generator yielding validated EvaluationEvents.
 */
export async function fetchEvaluationStream(
  options: FetchEvaluationOptions
): Promise<AsyncGenerator<EvaluationEvent, void, unknown>> {
  const baseUrl = (
    options.apiUrl ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  ).replace(/\/$/, "");

  const traceparent = options.traceparent || generateTraceparent();

  const formData = new FormData();
  formData.append("file", options.file);
  formData.append("turnstile_token", options.turnstileToken);

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/evaluations`, {
      method: "POST",
      body: formData,
      headers: {
        traceparent,
      },
      signal: options.signal,
    });
  } catch (err) {
    if (options.signal?.aborted) {
      throw err;
    }
    throw new ServiceUnavailableError(
      PRE_STREAM_UNAVAILABLE
    );
  }

  if (response.status === 503) {
    let apiError: ApiError | undefined;
    try {
      const data = await response.json();
      const parsed = zApiError.safeParse(data);
      if (parsed.success) apiError = parsed.data;
    } catch {
      // Ignored
    }
    throw new ServiceUnavailableError(
      apiError?.message ||
        PRE_STREAM_UNAVAILABLE,
      apiError
    );
  }

  if (!response.ok) {
    let apiError: ApiError | undefined;
    try {
      const data = await response.json();
      const parsed = zApiError.safeParse(data);
      if (parsed.success) apiError = parsed.data;
    } catch {
      // Ignored
    }
    throw new ApiStreamError(
      apiError?.message || `Evaluation request failed with status ${response.status}`,
      response.status,
      apiError
    );
  }

  if (!response.body) {
    throw new StreamParseError("Evaluation response body is empty", "");
  }

  return parseNDJSONStream(response.body);
}
