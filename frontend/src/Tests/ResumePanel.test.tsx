import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ResumePanel } from "@/components/landing/stream/ResumePanel";

describe("ResumePanel Component", () => {
  const defaultProps = {
    resultsStatus: null,
    isStreaming: false,
    clausesToCheck: null,
    turnstileKey: 0,
    onCheckClauses: vi.fn(),
    onSecurityCheckError: vi.fn(),
  };

  it("renders status text when resultsStatus is set", () => {
    const markup = renderToStaticMarkup(
      <ResumePanel {...defaultProps} resultsStatus="Connection dropped." />
    );
    expect(markup).toContain("Connection dropped.");
    expect(markup).toContain('role="status"');
  });

  it("renders checking text when idle and clausesToCheck is present", () => {
    const mockClauses = [
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
      <ResumePanel
        {...defaultProps}
        isStreaming={false}
        clausesToCheck={mockClauses}
      />
    );
    expect(markup).toContain("Checking 1 clause again after a quick security check.");
  });
});
