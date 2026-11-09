import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { FailuresList } from "@/components/results/FailuresList";
import type { ClauseFailure } from "@/lib/api/generated/types.gen";

const mockFailures: ClauseFailure[] = [
  {
    clause_id: "c-fail-1",
    reason: "rate_limited",
    retryable: true,
  },
];

describe("FailuresList", () => {
  it("renders notChecked alert when count is greater than zero", () => {
    const html = renderToStaticMarkup(
      <FailuresList
        failures={[]}
        notCheckedCount={2}
        clauseLookup={new Map()}
        onRetry={vi.fn()}
        retryingClauseId={null}
      />
    );

    expect(html).toContain("2 clauses aren&#x27;t checked yet.");
  });

  it("renders failed clauses section when failures exist", () => {
    const html = renderToStaticMarkup(
      <FailuresList
        failures={mockFailures}
        notCheckedCount={0}
        clauseLookup={new Map([["c-fail-1", { number: "4.1", heading: "Audit" }]])}
        onRetry={vi.fn()}
        retryingClauseId={null}
      />
    );

    expect(html).toContain("failed-clauses-section");
    expect(html).toContain("Audit");
  });
});
