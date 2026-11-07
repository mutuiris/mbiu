import type { ClauseResult, ImpactInputs, MoneyBasis } from "./api/generated/types.gen";

export interface ImpactCalculation {
  /** The example gross revenue used for calculation in Kenyan Shillings */
  revenueGross: number;
  /** Royalty rate percentage (e.g. 15 for 15%) */
  royaltyRate: number;
  /** Money basis: "gross" or "net" */
  basis: MoneyBasis;
  /** Total example deductions applied in Kenyan Shillings */
  totalDeductions: number;
  /** Net revenue available after deductions (min 0) */
  netRevenue: number;
  /** The calculated artist payout in whole Kenyan Shillings for the active contract terms */
  artistEarnings: number;
  /** What the artist would have received if royalties were calculated on Gross */
  earningsUnderGross: number;
  /** What the artist receives when royalties are calculated on Net after deductions */
  earningsUnderNet: number;
  /** The monetary amount lost to deductions (earningsUnderGross - earningsUnderNet) */
  lossToDeductions: number;
  /** Quoted basis quote text from contract if available */
  quotedBasisText?: string | null;
  /** Quoted rate quote text from contract if available */
  quotedRateText?: string | null;
  /** Quoted deduction names from contract */
  deductionQuotes: string[];
}

/** Default example gross revenue in Kenyan Shillings (KES 100,000) */
export const DEFAULT_EXAMPLE_GROSS = 100_000;

/** Default example deduction amount in Kenyan Shillings (KES 40,000) */
export const DEFAULT_EXAMPLE_DEDUCTIONS = 40_000;

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
 * Calculates a worked example in Kenyan Shillings based on impact_inputs and optional user adjustments.
 *
 * Rules:
 * 1. Gross vs Net: Under Gross, royalty rate applies directly to gross revenue.
 *    Under Net, deductions are subtracted before the royalty rate applies.
 * 2. Deductions before royalties: Net revenue cannot be negative (floored at 0).
 * 3. Zero and very large values: Handles 0, very large numbers safely without NaN.
 * 4. Rounding: All currency amounts are strictly rounded to whole shillings (Math.round).
 */
export function calculateImpact(
  inputs: ImpactInputs | null | undefined,
  customGross: number = DEFAULT_EXAMPLE_GROSS,
  customDeductions?: number,
): ImpactCalculation | null {
  if (!hasClearFormula(inputs)) {
    return null;
  }

  // Ensure gross revenue is a non-negative finite number
  const safeGross = Math.max(0, Number.isFinite(customGross) ? customGross : 0);

  const safeRate = Math.max(0, inputs?.royalty_rate_percent?.value ?? 0);

  // Basis: "net" if money_basis says net or if deductions are defined; otherwise "gross"
  const rawBasis = inputs?.money_basis?.value;
  const basis: MoneyBasis = rawBasis === "gross" ? "gross" : "net";

  // Deductions: if custom specified, use that; otherwise use default or proportional
  const deductionCount = inputs?.deductions?.length ?? 0;
  const defaultDed = deductionCount > 0 ? DEFAULT_EXAMPLE_DEDUCTIONS : 0;
  const rawDeductions = customDeductions !== undefined ? customDeductions : defaultDed;
  const safeDeductions = Math.max(0, Number.isFinite(rawDeductions) ? rawDeductions : 0);

  // Net revenue cannot fall below 0
  const netRevenue = Math.max(0, safeGross - safeDeductions);

  // Earnings calculations rounded to whole shillings
  const earningsUnderGross = Math.round(safeGross * (safeRate / 100));
  const earningsUnderNet = Math.round(netRevenue * (safeRate / 100));

  const artistEarnings = basis === "gross" ? earningsUnderGross : earningsUnderNet;
  const lossToDeductions = Math.max(0, earningsUnderGross - earningsUnderNet);

  const deductionQuotes = inputs?.deductions?.map((d) => d.quote || d.value) || [];

  return {
    revenueGross: Math.round(safeGross),
    royaltyRate: safeRate,
    basis,
    totalDeductions: Math.round(safeDeductions),
    netRevenue: Math.round(netRevenue),
    artistEarnings,
    earningsUnderGross,
    earningsUnderNet,
    lossToDeductions,
    quotedBasisText: inputs?.money_basis?.quote,
    quotedRateText: inputs?.royalty_rate_percent?.quote,
    deductionQuotes,
  };
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
