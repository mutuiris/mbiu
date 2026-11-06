import type { ClauseResult } from "./api/generated/types.gen";

export type OutcomeTone = "typical" | "unusual" | "inquiry" | "unchecked";

export interface OutcomeLabel {
  label: string;
  tone: OutcomeTone;
}

/**
 * The words an artist sees for each comparison outcome. The backend keeps the finer
 * outcomes; cards only say whether a clause is typical, unusual or worth asking about.
 */
export function outcomeLabel(comparison: ClauseResult["comparison"]): OutcomeLabel {
  switch (comparison) {
    case "matches_standard":
    case "better_for_you":
      return { label: "Typical", tone: "typical" };
    case "not_in_standard":
      return { label: "Unusual", tone: "unusual" };
    case "worse_for_you":
    case "missing_from_contract":
      return { label: "Worth inquiry", tone: "inquiry" };
    default:
      return { label: "Couldn't check", tone: "unchecked" };
  }
}
