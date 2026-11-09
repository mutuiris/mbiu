import type { ClauseResult, ImpactInputs } from "./api/generated/types.gen";

/**
 * A clear formula needs a stated royalty rate. Without one there is nothing to calculate,
 * and inventing a rate would show the artist a number their contract never gave.
 */
export function hasClearFormula(inputs: ImpactInputs | null | undefined): boolean {
  const rate = inputs?.royalty_rate_percent?.value;
  return rate != null && Number.isFinite(rate);
}

/**
 * Determines whether a clause is considered "high impact" according to Mbiu's system architecture:
 * - Direct financial implications (royalties, revenue, deductions, calculations)
 * - Rights & ownership (master recordings, copyright, moral rights, publishing, assignments)
 * - Advance recoupment & accounting/audit
 * - Term, exclusivity, post-term restrictions, non-compete
 * - Termination, breaches, remedies, rights reversion
 * - Warranties, indemnities, liability
 * - Material deviations (worse_for_you, not_in_standard, missing_from_contract, better_for_you)
 * - Contract-wide conflicts or overrides
 *
 * Low-impact / standard boilerplate clauses (notices, governing law, counterparts, severability,
 * typical administrative definitions) are collapsed/grouped to reduce feed clutter.
 */
export function isHighImpactClause(
  result: ClauseResult,
  extraHeading?: string | null,
  hasContractIssue: boolean = false,
): boolean {
  // Any clause involved in a contract issue (conflict or override) is high impact
  if (hasContractIssue) {
    return true;
  }

  // Any deviation or non-standard outcome is high impact
  if (
    result.comparison === "worse_for_you" ||
    result.comparison === "not_in_standard" ||
    result.comparison === "missing_from_contract" ||
    result.comparison === "better_for_you"
  ) {
    return true;
  }

  // Any clause with clear monetary formula / calculations or deductions is high impact
  if (
    result.impact_inputs &&
    (hasClearFormula(result.impact_inputs) ||
      (result.impact_inputs.deductions && result.impact_inputs.deductions.length > 0))
  ) {
    return true;
  }

  // Check text, headline, and heading for high-impact topics
  const combined = `${extraHeading ?? ""} ${result.headline} ${result.what_it_says} ${result.original_text}`.toLowerCase();

  const HIGH_IMPACT_PATTERNS = [
    /\broyalt/i,
    /\badvance\b/i,
    /\brecoup/i,
    /\baccounting\b/i,
    /\baudit\b/i,
    /\bpayment\b/i,
    /\bnet receipts\b/i,
    /\bgross receipts\b/i,
    /\bdeduction/i,
    /\bownership\b/i,
    /\bmaster(?:s)?\b/i,
    /\bcopyright/i,
    /\bgrant of rights\b/i,
    /\bmoral rights\b/i,
    /\bassign(?:ment|s)?\b/i,
    /\bwork for hire\b/i,
    /\bpublishing\b/i,
    /\bexclusiv/i,
    /\bpost-term\b/i,
    /\bnon-compete\b/i,
    /\brestrict/i,
    /\bterritory\b/i,
    /\bterm\b/i,
    /\btermination\b/i,
    /\bbreach\b/i,
    /\breversion\b/i,
    /\bindemn/i,
    /\bwarrant/i,
    /\bliabilit/i,
  ];

  for (const pattern of HIGH_IMPACT_PATTERNS) {
    if (pattern.test(combined)) {
      return true;
    }
  }

  return false;
}
