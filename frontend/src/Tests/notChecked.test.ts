import { describe, expect, it } from "vitest";
import { notCheckedMessage } from "@/components/results/LiveResults";

describe("notCheckedMessage", () => {
  it("says the most important clauses came first and how many are left", () => {
    expect(notCheckedMessage(1)).toBe(
      "Mbiu checked the most important clauses first. 1 clause isn't checked yet.",
    );
    expect(notCheckedMessage(4)).toBe(
      "Mbiu checked the most important clauses first. 4 clauses aren't checked yet.",
    );
  });
});
