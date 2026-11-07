import { describe, expect, it } from "vitest";
import { outcomeLabel } from "./outcome";

describe("outcomeLabel", () => {
  it("shows every outcome with strict neutral symbols and labels per architecture doc", () => {
    expect(outcomeLabel("matches_standard")).toEqual({
      label: "Typical",
      symbol: "🔵",
      tone: "typical",
      display: "🔵 Typical",
    });
    expect(outcomeLabel("better_for_you")).toEqual({
      label: "Typical",
      symbol: "🔵",
      tone: "typical",
      display: "🔵 Typical",
    });
    expect(outcomeLabel("not_in_standard")).toEqual({
      label: "Unusual",
      symbol: "🟡",
      tone: "unusual",
      display: "🟡 Unusual",
    });
    expect(outcomeLabel("worse_for_you")).toEqual({
      label: "Worth asking about",
      symbol: "🟠",
      tone: "worth_asking_about",
      display: "🟠 Worth asking about",
    });
    expect(outcomeLabel("missing_from_contract")).toEqual({
      label: "Worth asking about",
      symbol: "🟠",
      tone: "worth_asking_about",
      display: "🟠 Worth asking about",
    });
    expect(outcomeLabel("cannot_compare")).toEqual({
      label: "Couldn't compare",
      symbol: "⚪",
      tone: "cannot_compare",
      display: "⚪ Couldn't compare",
    });
  });
});
