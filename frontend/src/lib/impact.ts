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
 * Formats a numeric amount into whole Kenyan Shillings.
 * Always rounds to the nearest whole integer.
 * Example: 15000 -> "KES 15,000"
 */
export function formatShillings(amount: number): string {
  if (!Number.isFinite(amount) || Number.isNaN(amount)) {
    return "KES 0";
  }
  const rounded = Math.round(amount);
  const normalized = Object.is(rounded, -0) || rounded === 0 ? 0 : rounded;
  return `KES ${normalized.toLocaleString("en-KE")}`;
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

/** Example amount the label receives in the shillings steps (KES 1,000,000). */
export const EXAMPLE_GROSS = 1_000_000;

export interface DeductionStep {
  label: string;
  quote: string;
  percent: number | null;
  amount: number | null;
}

export interface ShillingSteps {
  gross: number;
  steps: DeductionStep[];
  base: number;
  /** True when a quoted deduction has no stated amount, so the real base is lower. */
  baseIsCeiling: boolean;
  ratePercent: number | null;
  ratePhrase: string | null;
  youReceive: number | null;
}

const PERCENT = /(\d+(?:\.\d+)?)\s*%/;

const sentenceCase = (text: string) => (text ? text[0].toUpperCase() + text.slice(1) : text);

/**
 * Shows what quoted deductions take from an example amount. Only figures the contract quotes
 * are used: a deduction without a stated percentage is listed without an amount, and
 * "You receive" appears only when the contract states the royalty rate.
 */
export function shillingSteps(
  inputs: ImpactInputs | null | undefined,
  gross: number,
): ShillingSteps | null {
  if (!inputs) return null;
  const rate = inputs.royalty_rate_percent;
  const ratePercent = rate != null && Number.isFinite(rate.value) ? rate.value : null;
  let left = Math.max(0, Math.round(gross));
  const start = left;
  const steps = inputs.deductions.map((d): DeductionStep => {
    const match = d.value.match(PERCENT) ?? d.quote.match(PERCENT);
    const percent = match ? Number(match[1]) : null;
    const amount = percent == null ? null : Math.min(left, Math.round((left * percent) / 100));
    if (amount != null) left -= amount;
    const label = sentenceCase(d.value.replace(PERCENT, "").replace(/\s+/g, " ").trim()) || d.value;
    return { label, quote: d.quote, percent, amount };
  });
  if (ratePercent == null && steps.every((s) => s.percent == null)) return null;
  return {
    gross: start,
    steps,
    base: left,
    baseIsCeiling: steps.some((s) => s.amount == null),
    ratePercent,
    ratePhrase: rate?.quote ?? null,
    youReceive: ratePercent == null ? null : Math.round((left * ratePercent) / 100),
  };
}
