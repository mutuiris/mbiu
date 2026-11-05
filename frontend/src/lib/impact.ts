import type { ImpactInputs, MoneyBasis } from "./api/generated/types.gen";

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
 * Checks whether the clause impact inputs contain a clear formula
 * (e.g. specified royalty percentage, gross/net basis, or listed deductions).
 */
export function hasClearFormula(inputs: ImpactInputs | null | undefined): boolean {
  if (!inputs) return false;
  const hasRate = inputs.royalty_rate_percent != null && inputs.royalty_rate_percent.value != null;
  const hasBasis = inputs.money_basis != null && inputs.money_basis.value != null;
  const hasDeductions = Array.isArray(inputs.deductions) && inputs.deductions.length > 0;
  return Boolean(hasRate || hasBasis || hasDeductions);
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

  // Royalty rate percentage (default to 15% if only deductions are stated)
  const rawRate = inputs?.royalty_rate_percent?.value;
  const safeRate = Number.isFinite(rawRate) && rawRate != null ? Math.max(0, rawRate) : 15;

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
