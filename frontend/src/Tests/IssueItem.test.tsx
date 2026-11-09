import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { IssueItem } from "@/components/results/IssueItem";
import type { ContractIssue } from "@/lib/api/generated/types.gen";

const mockIssue: ContractIssue = {
  clause_ids: ["c-1", "c-2"],
  pages: [3, 9],
  kind: "conflict",
  explanation: "Clause 3.1 directly contradicts clause 9.2.",
  quotes: ["First quote text", "Second quote text"],
};

describe("IssueItem", () => {
  it("renders conflict badge, explanation, locations and quote block", () => {
    const html = renderToStaticMarkup(
      <IssueItem issue={mockIssue} index={0} />
    );

    expect(html).toContain("Contradiction / Conflict");
    expect(html).toContain("Clause 3.1 directly contradicts clause 9.2.");
    expect(html).toContain("Page 3, clause c-1");
    expect(html).toContain("Page 3, clause c-2");
    expect(html).toContain("First quote text");
    expect(html).toContain("Second quote text");
  });
});
