import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ResumeButton } from "@/components/landing/stream/ResumeButton";

describe("ResumeButton Component", () => {
  it("renders nothing when unfinished clauses array is empty", () => {
    const markup = renderToStaticMarkup(
      <ResumeButton unfinished={[]} onClick={vi.fn()} />
    );
    expect(markup).toBe("");
  });

  it("renders button with singular phrasing for 1 unfinished clause", () => {
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
      <ResumeButton unfinished={mockClauses} onClick={vi.fn()} />
    );
    expect(markup).toContain("Check the unfinished clause");
  });

  it("renders button with plural phrasing for multiple unfinished clauses", () => {
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
    const markup = renderToStaticMarkup(
      <ResumeButton unfinished={mockClauses} onClick={vi.fn()} />
    );
    expect(markup).toContain("Check the 2 unfinished clauses");
  });
});
