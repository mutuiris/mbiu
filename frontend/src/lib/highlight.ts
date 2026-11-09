/**
 * Finds which pdf.js text items on a page belong to a clause.
 *
 * The backend's character offsets come from its own text extraction, which pdf.js does not
 * reproduce exactly, so the clause is matched by its text instead. Whitespace is ignored on
 * both sides because pdf.js splits lines and words into items in its own way.
 */

/** Where this page sits within the clause's pages. */
export type PagePosition = "only" | "first" | "middle" | "last";

// Probe lengths tried in turn: long ones are unique on a page, short ones still match a
// clause that has only a line or two on its first or last page
const PROBE_LENGTHS = [60, 30, 15];

const squash = (text: string) => text.replace(/\s+/g, "").toLowerCase();

/** Finds the clause's start (or end) on the page, returning [index, probe length]. */
function locate(page: string, clause: string, fromEnd: boolean, after = 0): [number, number] {
  for (const length of PROBE_LENGTHS) {
    const probe = fromEnd ? clause.slice(-length) : clause.slice(0, length);
    const at = fromEnd ? page.indexOf(probe, after) : page.indexOf(probe);
    if (at >= 0) return [at, probe.length];
  }
  return [-1, 0];
}

export function pagePosition(page: number, clausePages: readonly number[]): PagePosition | null {
  const pages = [...clausePages].sort((a, b) => a - b);
  if (!pages.includes(page)) return null;
  if (pages.length === 1) return "only";
  if (page === pages[0]) return "first";
  if (page === pages[pages.length - 1]) return "last";
  return "middle";
}

export function highlightedItems(
  items: readonly string[],
  clauseText: string,
  position: PagePosition,
): Set<number> {
  const marked = new Set<number>();
  const clause = squash(clauseText);
  if (!clause) return marked;

  let page = "";
  const spans = items.map((item) => {
    const start = page.length;
    page += squash(item);
    return [start, page.length] as const;
  });

  let from = 0;
  let to = page.length;
  if (position === "only" || position === "first") {
    [from] = locate(page, clause, false);
    if (from < 0) return marked;
  }
  if (position === "only" || position === "last") {
    const [at, length] = locate(page, clause, true, from);
    if (at < 0) return marked;
    to = at + length;
  }

  spans.forEach(([start, end], index) => {
    if (end > start && start < to && end > from) marked.add(index);
  });
  return marked;
}

/** Text from a PDF goes into the text layer as HTML, so it must be escaped first. */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
