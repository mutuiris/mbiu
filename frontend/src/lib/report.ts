import type { Ask, ClauseResult } from "./api/generated/types.gen";
import { sortByImpactOrder } from "./api/stream";
import { isHighImpactClause } from "./impact";
import { outcomeLabel, type OutcomeTone } from "./outcome";

/** A question to ask, with every clause it came from. */
export interface MergedAsk {
  question: string;
  clauseIds: string[];
}

const FILLER = new Set([
  "could",
  "would",
  "should",
  "that",
  "this",
  "from",
  "with",
  "your",
  "remove",
  "agree",
  "they",
  "them",
  "have",
]);

const normalise = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}%\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();

const numbersIn = (text: string) =>
  new Set((text.match(/\d+(?:\.\d+)?/g) ?? []).map((n) => String(Number(n))));

const keyWordsIn = (text: string) =>
  new Set(normalise(text).split(" ").filter((w) => w.length >= 4 && !FILLER.has(w)));

function sameQuestion(a: string, b: string): boolean {
  if (normalise(a) === normalise(b)) return true;
  const numbersA = numbersIn(a);
  if (![...numbersIn(b)].some((n) => numbersA.has(n))) return false;
  const wordsA = keyWordsIn(a);
  const wordsB = keyWordsIn(b);
  const shared = [...wordsB].filter((w) => wordsA.has(w)).length;
  // Share of the shorter question's key words that also appear in the other one
  return shared / Math.max(1, Math.min(wordsA.size, wordsB.size)) >= 0.4;
}

/**
 * The model often asks the same thing twice for related clauses, worded differently.
 * Questions that quote the same number and mostly use the same words become one.
 */
export function mergeAsks(asks: readonly Ask[]): MergedAsk[] {
  const merged: MergedAsk[] = [];
  for (const ask of asks) {
    const match = merged.find((m) => sameQuestion(m.question, ask.question));
    const target = match ?? { question: ask.question, clauseIds: [] };
    if (!match) merged.push(target);
    if (ask.clause_id && !target.clauseIds.includes(ask.clause_id)) target.clauseIds.push(ask.clause_id);
  }
  return merged;
}

interface ClauseNaming {
  number?: string | null;
  heading?: string | null;
  text?: string | null;
}

// Real numbering only: "4", "4.1", "1.12(b)", "(b)", "7A". The backend uses slugs such as
// "1_2" or "preamble" for unnumbered clauses, which artists must never see.
const NUMBERING = /^(?:\d+[a-z]?(?:\.\d+[a-z]?)*)?(?:\([a-z0-9]+\))*$/i;

/** The clause number to show, or null when the backend gave an internal slug. */
export function displayNumber(number: string | null | undefined): string | null {
  const trimmed = number?.trim();
  return trimmed && NUMBERING.test(trimmed) ? trimmed : null;
}

/** A clause name an artist can read. Internal ids such as "7.2_2" never show. */
export function readableClauseName(clause: ClauseNaming | undefined): string {
  const number = displayNumber(clause?.number);
  let label = clause?.heading?.trim() || undefined;
  if (!label) {
    const words = clause?.text?.trim().split(/\s+/).filter(Boolean) ?? [];
    // Clause text often starts with its own number ("1.1", "(b)"); don't repeat it
    while (number && words.length && number.endsWith(words[0].replace(/[.:]$/, ""))) words.shift();
    label = words.length > 6 ? `${words.slice(0, 6).join(" ")}…` : words.join(" ") || undefined;
  }
  if (number && label) return `Clause ${number} · ${label}`;
  if (number) return `Clause ${number}`;
  return label ?? "A clause in your contract";
}

/** Reference excerpts can be blank template forms; strip markdown and fill-in blanks. */
export function cleanReferenceText(text: string): string {
  return text
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/#+\s*/g, "")
    .replace(/(\*\*|__)/g, "")
    .replace(/[.…_]{2,}/g, " ")
    .replace(/\s+([.,;:])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

export interface GroupedResults {
  /** Full cards, most important first. */
  cards: ClauseResult[];
  /** Low-impact standard and boilerplate clauses, folded. */
  standard: ClauseResult[];
  /** Results with no usual contract to compare against, folded into one row. */
  cannotCompare: ClauseResult[];
  /** What the PDF writes up in full: the cards plus important couldn't-compare clauses. */
  writeUps: ClauseResult[];
  counts: Record<OutcomeTone, number>;
}

/** Splits checked clauses into what gets a full card and what folds away. */
export function groupResults(
  results: readonly ClauseResult[],
  lookup: ReadonlyMap<string, { heading?: string | null }>,
  issueClauseIds: ReadonlySet<string>,
): GroupedResults {
  const cards: ClauseResult[] = [];
  const standard: ClauseResult[] = [];
  const cannotCompare: ClauseResult[] = [];
  const counts: Record<OutcomeTone, number> = { typical: 0, unusual: 0, worth_asking_about: 0, cannot_compare: 0 };
  for (const r of results) {
    counts[outcomeLabel(r.comparison).tone] += 1;
    const inIssue = issueClauseIds.has(r.clause_id);
    if (r.comparison === "cannot_compare" && !inIssue) cannotCompare.push(r);
    else if (isHighImpactClause(r, lookup.get(r.clause_id)?.heading, inIssue)) cards.push(r);
    else standard.push(r);
  }
  const importantUncompared = cannotCompare.filter((r) =>
    isHighImpactClause(r, lookup.get(r.clause_id)?.heading, false),
  );
  const sortedCards = sortByImpactOrder(cards);
  return { cards: sortedCards, standard, cannotCompare, writeUps: [...sortedCards, ...importantUncompared], counts };
}
