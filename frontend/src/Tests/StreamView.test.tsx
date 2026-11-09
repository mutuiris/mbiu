import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StreamView } from "@/components/landing/stream/StreamView";
import type { Clause } from "@/lib/api/generated/types.gen";
import type { EvaluationEvent } from "@/lib/api/stream";

async function* dummyStream(): AsyncGenerator<EvaluationEvent, void, unknown> {
  // empty generator
}

describe("StreamView Component", () => {
  const defaultProps = {
    stream: dummyStream(),
    selectedFile: null,
    isStreaming: false,
    keptSince: null,
    clausesToCheck: null,
    unfinished: [] as Clause[],
    resultsStatus: null,
    turnstileKey: 0,
    onKeepChange: vi.fn(),
    onStartOver: vi.fn(),
    onCheckClauses: vi.fn(),
    onCheckUnfinished: vi.fn(),
    onSecurityCheckError: vi.fn(),
  };

  it("renders stream controls and start over button", () => {
    const markup = renderToStaticMarkup(<StreamView {...defaultProps} />);
    expect(markup).toContain("Check another contract");
    expect(markup).toContain("restart-btn");
  });

  it("renders status message in resume panel when provided", () => {
    const markup = renderToStaticMarkup(
      <StreamView {...defaultProps} resultsStatus="The connection dropped." />
    );
    expect(markup).toContain("The connection dropped.");
  });

  it("renders unfinished clauses button when idle with unfinished clauses", () => {
    const singleUnfinished: Clause[] = [
      {
        clause_id: "c1",
        number: "1.1",
        text: "Sample text",
        heading: "Heading",
        pages: [1],
        start: 0,
        end: 11,
        section_id: "s1",
      },
    ];
    const markup = renderToStaticMarkup(
      <StreamView {...defaultProps} isStreaming={false} unfinished={singleUnfinished} />
    );
    expect(markup).toContain("Check the unfinished clause");

    const multipleUnfinished: Clause[] = [
      ...singleUnfinished,
      {
        clause_id: "c2",
        number: "1.2",
        text: "Sample text 2",
        heading: "Heading 2",
        pages: [2],
        start: 12,
        end: 25,
        section_id: "s1",
      },
    ];
    const markupMulti = renderToStaticMarkup(
      <StreamView {...defaultProps} isStreaming={false} unfinished={multipleUnfinished} />
    );
    expect(markupMulti).toContain("Check the 2 unfinished clauses");
  });
});
