import type {
  ClauseResult,
  ContractMapPayload,
  DocumentPayload,
  Summary,
} from "@/lib/api/generated/types.gen";
import { outcomeLabel, type OutcomeTone } from "@/lib/outcome";
import { displayNumber, mergeAsks, readableClauseName } from "@/lib/report";

type Lookup = ReadonlyMap<string, { number?: string | null; heading?: string | null; pages?: number[] }>;

export interface ReportInput {
  document: DocumentPayload | null;
  results: readonly ClauseResult[];
  /** The clauses that get a full write-up, most important first. */
  cards: readonly ClauseResult[];
  contractMap: ContractMapPayload | null;
  summary: Summary | null;
  clauseLookup: Lookup;
  isStreaming: boolean;
  today: Date;
}

export interface ReportClause {
  title: string;
  label: string;
  pages: string;
  headline: string;
  inSimpleWords: string;
  whyItMatters: string;
  usual: string | null;
  ask: string | null;
  sources: string | null;
  exactWords: string;
}

export interface ReportData {
  fileName: string;
  date: string;
  scope: string;
  status: string;
  reportId: string;
  legend: { label: string; meaning: string }[];
  counts: { label: string; count: number }[];
  clashCount: number;
  missingCount: number;
  questions: { question: string; where: string | null }[];
  clashes: { kind: string; explanation: string; where: string; quotes: [string, string] }[];
  clauses: ReportClause[];
  missing: { title: string; ask: string }[];
  checklist: string[];
  smallPrint: string;
}

const LABEL: Record<OutcomeTone, string> = {
  typical: "[TYPICAL]",
  unusual: "[UNUSUAL]",
  worth_asking_about: "[WORTH INQUIRY]",
  cannot_compare: "[COULDN'T COMPARE]",
};

const LEGEND: ReportData["legend"] = [
  {
    label: LABEL.typical,
    meaning: "Usual contracts commonly include a clause with the same practical effect. Typical does not mean safe.",
  },
  {
    label: LABEL.unusual,
    meaning: "Not usually in standard contracts, but we found no major effect on your money, music, time or freedom.",
  },
  {
    label: LABEL.worth_asking_about,
    meaning: "Not usual, and it could affect your money, music, time or freedom to take other work.",
  },
  {
    label: LABEL.cannot_compare,
    meaning: "No usual contract on this topic to compare with, or the check could not run safely.",
  },
];

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
const withoutDisclaimer = (text: string) => text.replace(/\s*Mbiu reports that one clause[^.]*\./g, "").trim();

/** Everything the PDF shows, worked out without touching the browser. */
export function reportData(input: ReportInput): ReportData {
  const { document, results, cards, contractMap, summary, clauseLookup, isStreaming, today } = input;
  const total = document?.clauses.length ?? results.length;
  const pages = document?.page_count ?? 1;
  const iso = today.toLocaleDateString("en-CA", { timeZone: "Africa/Nairobi" });
  const where = (ids: string[]) => {
    const numbers = ids.map((id) => displayNumber(clauseLookup.get(id)?.number)).filter((n): n is string => !!n);
    const page = ids.map((id) => clauseLookup.get(id)?.pages?.[0]).find((p) => p != null);
    const parts = [numbers.length ? `Clause ${numbers.join(" and ")}` : null, page != null ? `page ${page}` : null];
    return parts.filter(Boolean).join(", ") || null;
  };

  const counts: Record<OutcomeTone, number> = { typical: 0, unusual: 0, worth_asking_about: 0, cannot_compare: 0 };
  for (const r of results) counts[outcomeLabel(r.comparison).tone] += 1;

  const merged = mergeAsks(summary?.top_asks ?? []);
  const checklist = mergeAsks([
    ...(summary?.top_asks ?? []),
    ...results.filter((r) => r.ask_them).map((r) => ({ clause_id: r.clause_id, question: r.ask_them! })),
    ...(summary?.missing_protections ?? []).map((m) => ({ clause_id: null, question: m.ask_them })),
  ]).map((m) => m.question);

  return {
    fileName: `mbiu-report-${iso}.pdf`,
    date: today.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "Africa/Nairobi" }),
    scope: `${plural(pages, "page")} · ${total} total clauses`,
    status: isStreaming
      ? `In progress (${results.length} of ${total} checked)`
      : `Completed (${plural(results.length, "clause")} evaluated)`,
    reportId: `MBIU-${today.getFullYear()}-${results.length}C`,
    legend: LEGEND,
    counts: (["typical", "unusual", "worth_asking_about", "cannot_compare"] as const).map((tone) => ({
      label: LABEL[tone],
      count: counts[tone],
    })),
    clashCount: contractMap?.issues.length ?? 0,
    missingCount: summary?.missing_protections.length ?? 0,
    questions: merged.slice(0, 3).map((m) => ({ question: m.question, where: where(m.clauseIds) })),
    clashes: (contractMap?.issues ?? []).map((issue) => ({
      kind: issue.kind === "override" ? "One clause cancels another" : "Two clauses disagree",
      explanation: withoutDisclaimer(issue.explanation),
      where: issue.clause_ids.map((id) => readableClauseName(clauseLookup.get(id))).join(" and "),
      quotes: [`“${issue.quotes[0]}”`, `“${issue.quotes[1]}”`],
    })),
    clauses: cards.map((r) => {
      const extra = clauseLookup.get(r.clause_id);
      const sources = r.evidence?.length
        ? [...new Set(r.evidence.map((e) => e.source_title))].join(" · ")
        : r.standard_template_id;
      return {
        title: readableClauseName({ number: extra?.number, heading: extra?.heading, text: r.original_text }),
        label: LABEL[outcomeLabel(r.comparison).tone],
        pages: r.pages.join(", "),
        headline: r.headline,
        inSimpleWords: r.what_it_says,
        whyItMatters: r.what_it_means,
        usual: r.comparison_note ?? null,
        ask: r.ask_them,
        sources: sources ?? null,
        exactWords: `“${r.original_text}”`,
      };
    }),
    missing: (summary?.missing_protections ?? []).map((m) => ({ title: m.title, ask: m.ask_them })),
    checklist,
    smallPrint: [
      "Made by Mbiu on the artist's own device. Mbiu does not store contracts.",
      summary ? `Model ${summary.versions.model}, reference set ${summary.versions.corpus}.` : null,
    ]
      .filter(Boolean)
      .join(" "),
  };
}

/**
 * The header logo, drawn exactly as the Navbar shows it: the horn (32 px tall), a 6 px gap and
 * "mbiu" in Manrope 800, 1.2rem, -0.06em tracking, ink colour. Drawn at 3x for print.
 */
async function logoDataUrl(): Promise<string | null> {
  try {
    const scale = 3;
    const horn = new window.Image();
    horn.src = "/brand/mbiu-horn.png";
    await horn.decode();
    const fontSize = 19.2 * scale;
    const font = `800 ${fontSize}px "Manrope Variable", Manrope, sans-serif`;
    await window.document.fonts.load(font, "mbiu");
    const hornHeight = 32 * scale;
    const hornWidth = (horn.naturalWidth / horn.naturalHeight) * hornHeight;
    const gap = 6 * scale;
    const canvas = window.document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.font = font;
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = `${-0.06 * fontSize}px`;
    const textWidth = ctx.measureText("mbiu").width;
    canvas.width = Math.ceil(hornWidth + gap + textWidth + 4);
    canvas.height = hornHeight;
    ctx.font = font;
    (ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = `${-0.06 * fontSize}px`;
    ctx.drawImage(horn, 0, 0, hornWidth, hornHeight);
    ctx.fillStyle = "#161a26";
    ctx.textBaseline = "middle";
    ctx.fillText("mbiu", hornWidth + gap, hornHeight / 2);
    return canvas.toDataURL("image/png");
  } catch {
    return null;
  }
}

/** Builds the PDF in the browser and saves it. The report never leaves the device. */
export async function downloadReport(data: ReportData): Promise<void> {
  await import("@/lib/browser-polyfills");
  const [{ pdf }, { ReportDocument }, logo] = await Promise.all([
    import("@react-pdf/renderer"),
    import("./ReportDocument"),
    logoDataUrl(),
  ]);
  const blob = await pdf(ReportDocument({ data, logo })).toBlob();
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = data.fileName;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
