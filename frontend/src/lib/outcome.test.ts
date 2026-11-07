import { describe, expect, it } from "vitest";
import { outcomeLabel } from "./outcome";

describe("outcomeLabel", () => {
  it("shows every outcome as typical, unusual, worth inquiry or couldn't check", () => {
    expect(outcomeLabel("matches_standard").label).toBe("Typical");
    expect(outcomeLabel("better_for_you").label).toBe("Typical");
    expect(outcomeLabel("not_in_standard").label).toBe("Unusual");
    expect(outcomeLabel("worse_for_you").label).toBe("Worth inquiry");
    expect(outcomeLabel("missing_from_contract").label).toBe("Worth inquiry");
    expect(outcomeLabel("cannot_compare").label).toBe("Couldn't check");
  });
});
