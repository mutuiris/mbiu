import type { ClauseResult } from "./api/generated/types.gen";

export type OutcomeTone = "typical" | "unusual" | "worth_asking_about" | "cannot_compare";

export interface OutcomeLabel {
  label: string;
  symbol: string;
  tone: OutcomeTone;
  display: string;
}

/**
 * The words an artist sees for each comparison outcome strictly aligned with
 * Mbiu system architecture and tooling:
 * - typical: 🔵 Typical
 * - unusual: 🟡 Unusual
 * - worth_asking_about: 🟠 Worth asking about
 * - cannot_compare: ⚪ Couldn't compare
 *
 * Typical does not mean safe. No green label is ever used.
 */
export function outcomeLabel(comparison: ClauseResult["comparison"]): OutcomeLabel {
  switch (comparison) {
    case "matches_standard":
    case "better_for_you":
      return {
        label: "Typical",
        symbol: "🔵",
        tone: "typical",
        display: "🔵 Typical",
      };
    case "not_in_standard":
      return {
        label: "Unusual",
        symbol: "🟡",
        tone: "unusual",
        display: "🟡 Unusual",
      };
    case "worse_for_you":
    case "missing_from_contract":
      return {
        label: "Worth asking about",
        symbol: "🟠",
        tone: "worth_asking_about",
        display: "🟠 Worth asking about",
      };
    default:
      return {
        label: "Couldn't compare",
        symbol: "⚪",
        tone: "cannot_compare",
        display: "⚪ Couldn't compare",
      };
  }
}
