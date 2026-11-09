import type {
  ClauseResult,
  ContractMapPayload,
  DocumentPayload,
  Summary,
} from "@/lib/api/generated/types.gen";
import { outcomeLabel } from "@/lib/outcome";

export interface ReportPdfParams {
  document: DocumentPayload | null;
  allResults: ClauseResult[];
  highImpactResults: ClauseResult[];
  contractMap: ContractMapPayload | null;
  summary: Summary | null;
  clauseLookup: Map<
    string,
    { number?: string | null; heading?: string | null; pages?: number[] }
  >;
  isStreaming?: boolean;
}

/**
 * Returns true when a standard_excerpt is a short, clean human-readable summary
 * rather than a raw multi-clause legal template dump from the corpus.
 */
export function isCleanShortExcerpt(excerpt: string | null | undefined): boolean {
  if (!excerpt) return false;
  const trimmed = excerpt.trim();
  if (!trimmed || trimmed.length > 180) return false;
  if (
    trimmed.includes("##") ||
    trimmed.includes("....") ||
    /\bIN WITNESS WHEREOF\b/i.test(trimmed) ||
    /\bshall be deemed\b/i.test(trimmed) ||
    /\bhereto\b/i.test(trimmed)
  ) {
    return false;
  }
  return true;
}

/**
 * Builds a plain-language summary explaining how a clause compares to reviewed
 * reference standards, avoiding raw multi-clause legal template dumps.
 */
export function formatHowItComparesSummary(result: ClauseResult): string {
  const sourceNames =
    result.evidence && result.evidence.length > 0
      ? Array.from(new Set(result.evidence.map((e) => e.source_title).filter(Boolean)))
      : [];
  const standardRef =
    sourceNames.length > 0
      ? `reviewed standards (${sourceNames.slice(0, 2).join(", ")})`
      : "reviewed music industry standards";

  let baseSummary: string;
  switch (result.comparison) {
    case "worse_for_you":
      baseSummary = `Less favorable than ${standardRef}. Standard agreements typically set fairer splits, clearer limits, or stronger protections for the artist on this term.`;
      break;
    case "missing_from_contract":
      baseSummary = `Missing a protection commonly found in ${standardRef}, which could leave your rights or payments less protected unless clarified.`;
      break;
    case "not_in_standard":
      baseSummary = `Not commonly found in ${standardRef}. While it may not have a major adverse effect on its own, it differs from standard industry practice.`;
      break;
    case "better_for_you":
      baseSummary = `More favorable to you than the baseline in ${standardRef}, giving you stronger or clearer protection.`;
      break;
    case "matches_standard":
      baseSummary = `Typical and consistent with how ${standardRef} handle this term.`;
      break;
    case "cannot_compare":
    default:
      baseSummary =
        "No direct match was available in our reference templates for this specific clause, so Mbiu explains what your contract says in plain language.";
      break;
  }

  const parts: string[] = [baseSummary];
  if (result.comparison_note && result.comparison_note.trim()) {
    parts.push(result.comparison_note.trim());
  }
  if (
    isCleanShortExcerpt(result.standard_excerpt) &&
    result.standard_excerpt &&
    result.standard_excerpt.trim() !== result.comparison_note?.trim()
  ) {
    parts.push(result.standard_excerpt.trim());
  }
  return parts.join(" ");
}

type PdfFont = "F1" | "F2" | "F3" | "F4" | "F5";

const PAGE_WIDTH = 595.28; // A4 width in pt
const PAGE_HEIGHT = 841.89; // A4 height in pt
const MARGIN_X = 48;
const MARGIN_TOP = 50;
const MARGIN_BOTTOM = 54;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN_X * 2;

/**
 * Converts Unicode text to WinAnsi-safe ASCII/Latin1 characters and escapes PDF string literals.
 */
function escapePdfText(input: string): string {
  const normalized = input
    .replace(/[\u201C\u201D\u201E\u201F]/g, '"')
    .replace(/[\u2018\u2019\u201A\u201B]/g, "'")
    .replace(/\u2014/g, " -- ")
    .replace(/\u2013/g, "-")
    .replace(/\u2026/g, "...")
    .replace(/\u2022/g, "*")
    .replace(/\u00A0/g, " ")
    .replace(/[^\x20-\x7E\xA1-\xFF]/g, "");

  return normalized
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)");
}

/**
 * Approximate character width in ems for Times / Helvetica so lines wrap cleanly.
 */
function estimateTextWidth(text: string, fontSize: number, bold = false): number {
  const avgFactor = bold ? 0.49 : 0.45;
  return text.length * fontSize * avgFactor;
}

function wrapText(text: string, maxWidth: number, fontSize: number, bold = false): string[] {
  const clean = text.replace(/\r\n/g, "\n").trim();
  if (!clean) return [""];

  const paragraphs = clean.split("\n");
  const lines: string[] = [];

  for (const para of paragraphs) {
    const words = para.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      lines.push("");
      continue;
    }
    let currentLine = words[0];
    for (let i = 1; i < words.length; i++) {
      const candidate = `${currentLine} ${words[i]}`;
      if (estimateTextWidth(candidate, fontSize, bold) <= maxWidth) {
        currentLine = candidate;
      } else {
        lines.push(currentLine);
        currentLine = words[i];
      }
    }
    lines.push(currentLine);
  }

  return lines;
}

export class PdfDocumentBuilder {
  private pages: string[][] = [[]];
  private cursorY: number = PAGE_HEIGHT - MARGIN_TOP;

  private get currentStream(): string[] {
    return this.pages[this.pages.length - 1];
  }

  public getCursorY(): number {
    return this.cursorY;
  }

  public ensureSpace(heightNeeded: number): void {
    if (this.cursorY - heightNeeded < MARGIN_BOTTOM) {
      this.newPage();
    }
  }

  public newPage(): void {
    this.pages.push([]);
    this.cursorY = PAGE_HEIGHT - MARGIN_TOP;
  }

  public addGap(pts: number): void {
    this.cursorY = Math.max(MARGIN_BOTTOM, this.cursorY - pts);
  }

  public drawHorizontalRule(gapBefore = 6, gapAfter = 10, thickness = 0.6): void {
    this.ensureSpace(gapBefore + gapAfter + 4);
    this.cursorY -= gapBefore;
    const y = this.cursorY.toFixed(2);
    this.currentStream.push(
      `q ${thickness} w 0.2 0.2 0.2 RG ${MARGIN_X} ${y} m ${(PAGE_WIDTH - MARGIN_X).toFixed(
        2,
      )} ${y} l S Q`,
    );
    this.cursorY -= gapAfter;
  }

  public drawCenteredTextBlock(
    text: string,
    options: {
      font?: PdfFont;
      fontSize?: number;
      lineHeight?: number;
      gapAfter?: number;
    } = {},
  ): void {
    const font = options.font ?? "F4";
    const fontSize = options.fontSize ?? 14;
    const lineHeight = options.lineHeight ?? fontSize * 1.35;
    const gapAfter = options.gapAfter ?? 4;
    const isBold = font === "F2" || font === "F4";

    const lines = wrapText(text, CONTENT_WIDTH, fontSize, isBold);
    for (const line of lines) {
      this.ensureSpace(lineHeight + 2);
      const lineWidth = estimateTextWidth(line, fontSize, isBold);
      const x = Math.max(MARGIN_X, MARGIN_X + (CONTENT_WIDTH - lineWidth) / 2);
      const y = (this.cursorY - fontSize).toFixed(2);
      this.currentStream.push(
        `BT /${font} ${fontSize} Tf 0 g ${x.toFixed(2)} ${y} Td (${escapePdfText(line)}) Tj ET`,
      );
      this.cursorY -= lineHeight;
    }
    this.cursorY -= gapAfter;
  }

  public drawTextBlock(
    text: string,
    options: {
      font?: PdfFont;
      fontSize?: number;
      lineHeight?: number;
      indent?: number;
      maxWidth?: number;
      colorGray?: number;
      gapAfter?: number;
    } = {},
  ): void {
    const font = options.font ?? "F3";
    const fontSize = options.fontSize ?? 10.5;
    const lineHeight = options.lineHeight ?? fontSize * 1.35;
    const indent = options.indent ?? 0;
    const maxWidth = options.maxWidth ?? CONTENT_WIDTH - indent;
    const colorGray = options.colorGray ?? 0;
    const gapAfter = options.gapAfter ?? 3;
    const isBold = font === "F2" || font === "F4";

    const lines = wrapText(text, maxWidth, fontSize, isBold);
    for (const line of lines) {
      this.ensureSpace(lineHeight + 2);
      if (line.length > 0) {
        const x = (MARGIN_X + indent).toFixed(2);
        const y = (this.cursorY - fontSize).toFixed(2);
        this.currentStream.push(
          `BT /${font} ${fontSize} Tf ${colorGray.toFixed(2)} g ${x} ${y} Td (${escapePdfText(
            line,
          )}) Tj ET`,
        );
      }
      this.cursorY -= lineHeight;
    }
    this.cursorY -= gapAfter;
  }

  public drawSectionHeading(title: string): void {
    this.ensureSpace(36);
    this.addGap(6);
    this.drawTextBlock(title, {
      font: "F4",
      fontSize: 12,
      lineHeight: 15,
      gapAfter: 2,
    });
    this.drawHorizontalRule(2, 8, 0.9);
  }

  public drawBoxedNotice(title: string, body: string): void {
    const lines = wrapText(body, CONTENT_WIDTH - 24, 9.5, false);
    const boxHeight = 18 + lines.length * 13 + 8;
    this.ensureSpace(boxHeight + 8);

    const topY = this.cursorY;
    const bottomY = topY - boxHeight;
    this.currentStream.push(
      `q 0.97 0.97 0.97 rg 0.25 0.25 0.25 RG 0.75 w ${MARGIN_X} ${bottomY.toFixed(
        2,
      )} ${CONTENT_WIDTH.toFixed(2)} ${boxHeight.toFixed(2)} re B Q`,
    );

    this.cursorY -= 6;
    this.drawTextBlock(title, {
      font: "F4",
      fontSize: 9.5,
      lineHeight: 13,
      indent: 12,
      maxWidth: CONTENT_WIDTH - 24,
      gapAfter: 2,
    });
    this.drawTextBlock(body, {
      font: "F3",
      fontSize: 9.2,
      lineHeight: 12.8,
      indent: 12,
      maxWidth: CONTENT_WIDTH - 24,
      gapAfter: 4,
    });
    this.cursorY = bottomY - 8;
  }

  public drawLeftBorderedQuote(quote: string, indent = 10): void {
    const maxWidth = CONTENT_WIDTH - indent - 12;
    const lines = wrapText(`"${quote}"`, maxWidth, 9.5, false);
    const blockHeight = lines.length * 13.5 + 4;
    this.ensureSpace(blockHeight + 6);

    const topY = this.cursorY;
    const bottomY = topY - blockHeight;

    // Left vertical border line
    const lineX = (MARGIN_X + indent).toFixed(2);
    this.currentStream.push(
      `q 2.5 w 0.45 0.45 0.45 RG ${lineX} ${bottomY.toFixed(2)} m ${lineX} ${topY.toFixed(
        2,
      )} l S Q`,
    );

    this.cursorY -= 2;
    for (const line of lines) {
      if (line.length > 0) {
        const textX = (MARGIN_X + indent + 8).toFixed(2);
        const textY = (this.cursorY - 9.5).toFixed(2);
        this.currentStream.push(
          `BT /F5 9.5 Tf 0.1 g ${textX} ${textY} Td (${escapePdfText(line)}) Tj ET`,
        );
      }
      this.cursorY -= 13.5;
    }
    this.cursorY = bottomY - 4;
  }

  /**
   * Draws a bordered table matching the styling of EvaluationReportModal tables.
   */
  public drawTable(options: {
    columnWidths: number[];
    headers: string[];
    rows: { cells: string[]; isBold?: boolean; alignCenter?: boolean[] }[];
  }): void {
    const { columnWidths, headers, rows } = options;
    const headerHeight = 22;

    // Estimate row heights
    const rowHeights = rows.map((r) => {
      let maxLines = 1;
      r.cells.forEach((cell, idx) => {
        const colW = columnWidths[idx] - 12;
        const lines = wrapText(cell, colW, 9.5, r.isBold ?? false);
        if (lines.length > maxLines) maxLines = lines.length;
      });
      return Math.max(22, maxLines * 13 + 8);
    });

    const totalTableHeight = headerHeight + rowHeights.reduce((a, b) => a + b, 0);
    this.ensureSpace(totalTableHeight + 6);

    const topY = this.cursorY;
    const bottomY = topY - totalTableHeight;

    // 1. Shaded header background
    this.currentStream.push(
      `q 0.94 0.94 0.94 rg ${MARGIN_X} ${(topY - headerHeight).toFixed(
        2,
      )} ${CONTENT_WIDTH.toFixed(2)} ${headerHeight} re f Q`,
    );

    // 2. Outer box
    this.currentStream.push(
      `q 0.7 w 0.2 0.2 0.2 RG ${MARGIN_X} ${bottomY.toFixed(2)} ${CONTENT_WIDTH.toFixed(
        2,
      )} ${totalTableHeight.toFixed(2)} re S Q`,
    );

    // 3. Header horizontal division
    this.currentStream.push(
      `q 0.6 w 0.2 0.2 0.2 RG ${MARGIN_X} ${(topY - headerHeight).toFixed(2)} m ${(
        PAGE_WIDTH - MARGIN_X
      ).toFixed(2)} ${(topY - headerHeight).toFixed(2)} l S Q`,
    );

    // 4. Vertical column borders
    let colX = MARGIN_X;
    for (let i = 0; i < columnWidths.length - 1; i++) {
      colX += columnWidths[i];
      this.currentStream.push(
        `q 0.5 w 0.3 0.3 0.3 RG ${colX.toFixed(2)} ${bottomY.toFixed(
          2,
        )} m ${colX.toFixed(2)} ${topY.toFixed(2)} l S Q`,
      );
    }

    // 5. Header texts
    let curX = MARGIN_X;
    headers.forEach((h, idx) => {
      const w = columnWidths[idx];
      const textX = (curX + 6).toFixed(2);
      const textY = (topY - 15).toFixed(2);
      this.currentStream.push(
        `BT /F4 9.5 Tf 0 g ${textX} ${textY} Td (${escapePdfText(h)}) Tj ET`,
      );
      curX += w;
    });

    // 6. Rows
    let currentY = topY - headerHeight;
    rows.forEach((row, rowIdx) => {
      const rHeight = rowHeights[rowIdx];
      const nextY = currentY - rHeight;

      // Row horizontal bottom border (if not last)
      if (rowIdx < rows.length - 1) {
        this.currentStream.push(
          `q 0.4 w 0.4 0.4 0.4 RG ${MARGIN_X} ${nextY.toFixed(2)} m ${(
            PAGE_WIDTH - MARGIN_X
          ).toFixed(2)} ${nextY.toFixed(2)} l S Q`,
        );
      }

      let cellX = MARGIN_X;
      row.cells.forEach((cell, colIdx) => {
        const colW = columnWidths[colIdx];
        const isCentered = row.alignCenter?.[colIdx] ?? false;
        const font: PdfFont = row.isBold ? "F4" : "F3";
        const fontSize = row.isBold ? 13 : 9.2;
        const lines = wrapText(cell, colW - 12, fontSize, row.isBold ?? false);

        let lineY = currentY - (row.isBold ? 16 : 14);
        for (const l of lines) {
          const lWidth = estimateTextWidth(l, fontSize, row.isBold ?? false);
          const drawX = isCentered
            ? cellX + (colW - lWidth) / 2
            : cellX + 6;
          this.currentStream.push(
            `BT /${font} ${fontSize} Tf 0 g ${drawX.toFixed(2)} ${lineY.toFixed(
              2,
            )} Td (${escapePdfText(l)}) Tj ET`,
          );
          lineY -= fontSize * 1.35;
        }
        cellX += colW;
      });

      currentY = nextY;
    });

    this.cursorY = bottomY - 10;
  }

  public build(footerLabel: string, footerVersions: string): Uint8Array {
    const totalPages = this.pages.length;

    // Add page footers matching EvaluationReportModal
    for (let i = 0; i < totalPages; i++) {
      const pageNum = i + 1;
      const stream = this.pages[i];
      const footerDividerY = 38;
      const footerTextY = 26;
      const footerSublineY = 15;

      // Divider line
      stream.push(
        `q 0.5 w 0.4 0.4 0.4 RG ${MARGIN_X} ${footerDividerY} m ${(
          PAGE_WIDTH - MARGIN_X
        ).toFixed(2)} ${footerDividerY} l S Q`,
      );

      // Line 1: Notice + Page Number
      stream.push(
        `BT /F3 8 Tf 0.25 g ${MARGIN_X} ${footerTextY} Td (${escapePdfText(
          footerLabel,
        )}) Tj ET`,
      );
      const pageLabel = `Page ${pageNum} of ${totalPages}`;
      const pageLabelX = PAGE_WIDTH - MARGIN_X - estimateTextWidth(pageLabel, 8, true);
      stream.push(
        `BT /F4 8 Tf 0.2 g ${pageLabelX.toFixed(2)} ${footerTextY} Td (${escapePdfText(
          pageLabel,
        )}) Tj ET`,
      );

      // Line 2: Version subline
      stream.push(
        `BT /F5 7.5 Tf 0.45 g ${MARGIN_X} ${footerSublineY} Td (${escapePdfText(
          footerVersions,
        )}) Tj ET`,
      );
    }

    // Object numbering:
    // 1: Catalog
    // 2: Pages
    // 3..7: Fonts F1..F5
    // For each page i (0..totalPages-1):
    //   pageObjId = 8 + i * 2
    //   contentObjId = 9 + i * 2
    const objects: string[] = [];
    const addObject = (id: number, body: string) => {
      objects[id] = `${id} 0 obj\n${body}\nendobj\n`;
    };

    addObject(1, "<< /Type /Catalog /Pages 2 0 R >>");

    const kids = Array.from({ length: totalPages }, (_, i) => `${8 + i * 2} 0 R`).join(" ");
    addObject(2, `<< /Type /Pages /Kids [${kids}] /Count ${totalPages} >>`);

    addObject(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
    addObject(
      4,
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    );
    addObject(
      5,
      "<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>",
    );
    addObject(
      6,
      "<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>",
    );
    addObject(
      7,
      "<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic /Encoding /WinAnsiEncoding >>",
    );

    for (let i = 0; i < totalPages; i++) {
      const pageObjId = 8 + i * 2;
      const contentObjId = 9 + i * 2;
      const contentStream = this.pages[i].join("\n");
      addObject(
        pageObjId,
        `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R /F5 7 0 R >> >> /Contents ${contentObjId} 0 R >>`,
      );
      addObject(
        contentObjId,
        `<< /Length ${contentStream.length} >>\nstream\n${contentStream}\nendstream`,
      );
    }

    let pdf = "%PDF-1.4\n";
    const offsets: number[] = [0];
    const maxObjId = 7 + totalPages * 2;

    for (let id = 1; id <= maxObjId; id++) {
      offsets[id] = pdf.length;
      pdf += objects[id];
    }

    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${maxObjId + 1}\n`;
    pdf += "0000000000 65535 f \n";
    for (let id = 1; id <= maxObjId; id++) {
      pdf += `${String(offsets[id]).padStart(10, "0")} 00000 n \n`;
    }

    pdf += `trailer\n<< /Size ${maxObjId + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;

    const encoder = new TextEncoder();
    return encoder.encode(pdf);
  }
}

/**
 * Generates the complete, multi-page A4 PDF report matching the exact 9-section
 * format, text, tables, and Times New Roman typography of EvaluationReportModal.
 */
export function generateEvaluationReportPdf(params: ReportPdfParams): Uint8Array {
  const {
    document,
    allResults,
    highImpactResults,
    contractMap,
    summary,
    clauseLookup,
    isStreaming = false,
  } = params;

  const pdf = new PdfDocumentBuilder();
  const currentDate = new Date().toLocaleDateString("en-KE", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const totalClauses = document?.clauses.length ?? allResults.length;
  const pageCount = document?.page_count ?? 1;

  let typical = 0;
  let unusual = 0;
  let worthAsking = 0;
  let cannotCompare = 0;
  for (const r of allResults) {
    const { tone } = outcomeLabel(r.comparison);
    if (tone === "typical") typical++;
    else if (tone === "unusual") unusual++;
    else if (tone === "worth_asking_about") worthAsking++;
    else cannotCompare++;
  }

  // Cover / Header: Centered 18pt bold title + 11.5pt italic subtitle
  pdf.drawCenteredTextBlock("MBIU CONTRACT EVALUATION REPORT", {
    font: "F4",
    fontSize: 18,
    lineHeight: 22,
    gapAfter: 2,
  });
  pdf.drawCenteredTextBlock(
    "Independent Objective Comparison with Standard Contract Templates",
    {
      font: "F5",
      fontSize: 11.5,
      lineHeight: 15,
      gapAfter: 8,
    },
  );

  // Metadata Grid: Bounded by horizontal rules
  pdf.drawHorizontalRule(2, 6, 0.75);
  const leftMeta1 = `Evaluation Date: ${currentDate}`;
  const rightMeta1 = `Contract Scope: ${pageCount} page${pageCount === 1 ? "" : "s"} * ${totalClauses} total clauses`;
  const leftMeta2 = `Analysis Status: ${
    isStreaming
      ? `In Progress (${allResults.length} clauses evaluated)`
      : `Completed (${allResults.length} clauses evaluated)`
  }`;
  const rightMeta2 = `Report ID: MBIU-${new Date().getFullYear()}-${allResults.length}C`;

  // Draw 2 metadata lines with 2 columns
  pdf.drawTextBlock(`${leftMeta1}${" ".repeat(8)}${rightMeta1}`, {
    font: "F3",
    fontSize: 9.5,
    lineHeight: 13,
    gapAfter: 2,
  });
  pdf.drawTextBlock(`${leftMeta2}${" ".repeat(8)}${rightMeta2}`, {
    font: "F3",
    fontSize: 9.5,
    lineHeight: 13,
    gapAfter: 6,
  });

  // Bordered IMPORTANT NOTICE box
  pdf.drawBoxedNotice(
    "IMPORTANT NOTICE (NOT LEGAL ADVICE):",
    "This report explains what the contract says compared with reviewed reference material. It does not judge whether any clause is lawful or enforceable, and it is not legal advice. Mbiu is an educational contract analysis tool designed to help artists understand practical implications for money, music, time, and freedom before negotiation.",
  );

  // Section 1: How to Read This Report (Exact 2-column table from modal)
  pdf.drawSectionHeading("1. How to Read This Report");
  pdf.drawTextBlock(
    "Every analyzed clause is categorized using one of four objective evaluation labels. Typical does not mean safe. A clause may be common in the music industry and still contain restrictive terms. Mbiu uses no green labels.",
    { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
  );

  pdf.drawTable({
    columnWidths: [115, CONTENT_WIDTH - 115],
    headers: ["Label", "Meaning for the Artist"],
    rows: [
      {
        cells: [
          "[TYPICAL]",
          "Typical of reference contract standards in our system. Reference contracts commonly include a clause with the same practical effect.",
        ],
      },
      {
        cells: [
          "[UNUSUAL]",
          "Not typically present in reference contract standards, but we found no major or meaningful adverse effect on your money, music, time, or freedom.",
        ],
      },
      {
        cells: [
          "[WORTH ASKING ABOUT]",
          "Not typical of reference contract standards, and could affect your money, music, time, or freedom to take other work in a minor or major way.",
        ],
      },
      {
        cells: [
          "[COULDN'T COMPARE]",
          "Insufficient reference standard templates on this topic, or comparison checks could not run safely. The plain-language explanation is still shown.",
        ],
      },
    ],
  });

  // Section 2: Executive Summary Dashboard (Exact 4-column summary table from modal)
  pdf.drawSectionHeading("2. Executive Summary Dashboard");
  const qCol = CONTENT_WIDTH / 4;
  pdf.drawTable({
    columnWidths: [qCol, qCol, qCol, qCol],
    headers: ["Typical", "Unusual", "Worth Asking About", "Couldn't Compare"],
    rows: [
      {
        cells: [
          String(typical),
          String(unusual),
          String(worthAsking),
          String(cannotCompare),
        ],
        isBold: true,
        alignCenter: [true, true, true, true],
      },
    ],
  });

  pdf.drawTextBlock(
    `Contract-wide contradictions or overrides: ${contractMap?.issues?.length ?? 0}`,
    { font: "F4", fontSize: 9.8, lineHeight: 13.5, gapAfter: 2 },
  );
  pdf.drawTextBlock(
    `Missing standard protections (reverse check): ${summary?.missing_protections?.length ?? 0}`,
    { font: "F4", fontSize: 9.8, lineHeight: 13.5, gapAfter: 6 },
  );

  if (summary?.top_asks && summary.top_asks.length > 0) {
    pdf.drawTextBlock("Priority Questions to Ask Counterparty:", {
      font: "F4",
      fontSize: 10.2,
      lineHeight: 14,
      gapAfter: 3,
    });
    summary.top_asks.slice(0, 3).forEach((ask, idx) => {
      pdf.drawTextBlock(`${idx + 1}. "${ask.question}"`, {
        font: "F4",
        fontSize: 9.8,
        lineHeight: 13.8,
        indent: 10,
        gapAfter: 2,
      });
    });
    pdf.addGap(4);
  }

  // Section 3: Contract-Wide Issues (Overrides & Conflicts)
  if (contractMap?.issues && contractMap.issues.length > 0) {
    pdf.drawSectionHeading("3. Contract-Wide Issues (Overrides & Conflicts)");
    pdf.drawTextBlock(
      "These clauses pull in different directions across pages or explicitly claim to override other terms. Mbiu reports what each clause says; it does not decide which clause a court would apply.",
      { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
    );

    contractMap.issues.forEach((issue, idx) => {
      pdf.ensureSpace(55);
      const c1 = clauseLookup.get(issue.clause_ids[0]);
      const c2 = clauseLookup.get(issue.clause_ids[1]);
      const loc1 = c1
        ? `Page ${c1.pages?.join(", ") ?? "?"}${c1.number ? `, clause ${c1.number}` : ""}`
        : issue.clause_ids[0];
      const loc2 = c2
        ? `Page ${c2.pages?.join(", ") ?? "?"}${c2.number ? `, clause ${c2.number}` : ""}`
        : issue.clause_ids[1];

      pdf.drawTextBlock(
        `Issue ${idx + 1} [${issue.kind.toUpperCase()}]: ${issue.explanation}`,
        { font: "F4", fontSize: 9.8, lineHeight: 13.5, gapAfter: 2 },
      );
      pdf.drawTextBlock(`Clauses involved: ${loc1} and ${loc2}`, {
        font: "F5",
        fontSize: 9.2,
        lineHeight: 13,
        indent: 10,
        gapAfter: 2,
      });
      if (issue.quotes && issue.quotes.length >= 2) {
        pdf.drawTextBlock(
          `Quotes: "${issue.quotes[0]}" vs "${issue.quotes[1]}"`,
          {
            font: "F5",
            fontSize: 9,
            lineHeight: 12.5,
            indent: 10,
            colorGray: 0.2,
            gapAfter: 6,
          },
        );
      }
    });
  }

  // Section 4: Breakdown of Evaluated Clauses
  pdf.drawSectionHeading("4. Breakdown of Evaluated Clauses");
  pdf.drawTextBlock(
    "The following clauses represent the key terms governing royalties, ownership, duration, restrictions, and liability.",
    { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
  );

  const orderedClauses = [
    ...highImpactResults,
    ...allResults.filter(
      (r) => !highImpactResults.some((h) => h.clause_id === r.clause_id),
    ),
  ];

  orderedClauses.forEach((result, idx) => {
    pdf.ensureSpace(115);
    const extra = clauseLookup.get(result.clause_id);
    const num = extra?.number
      ? extra.number.trim().toLowerCase().startsWith("clause")
        ? extra.number.trim()
        : `Clause ${extra.number.trim()}`
      : `Clause ${idx + 1}`;
    const topic = extra?.heading || "Contract Term";
    const { label } = outcomeLabel(result.comparison);
    const pages = result.pages.join(", ");

    // Clause Heading
    pdf.drawTextBlock(`4.${idx + 1} ${num}: ${topic} -- [${label.toUpperCase()}]`, {
      font: "F4",
      fontSize: 10.5,
      lineHeight: 14.5,
      gapAfter: 1,
    });
    pdf.drawTextBlock(`Location: Page ${pages}`, {
      font: "F5",
      fontSize: 9,
      lineHeight: 12.5,
      colorGray: 0.3,
      gapAfter: 3,
    });

    // What your contract says: Left-bordered italic quote
    pdf.drawTextBlock("What your contract says:", {
      font: "F4",
      fontSize: 9.5,
      lineHeight: 13,
      indent: 4,
      gapAfter: 1,
    });
    pdf.drawLeftBorderedQuote(result.what_it_says, 8);

    // In plain language
    pdf.drawTextBlock(`In plain language: ${result.headline}`, {
      font: "F4",
      fontSize: 9.5,
      lineHeight: 13.5,
      indent: 4,
      gapAfter: 2,
    });

    // Why this may matter to you
    pdf.drawTextBlock(`Why this may matter to you: ${result.what_it_means}`, {
      font: "F3",
      fontSize: 9.5,
      lineHeight: 13.5,
      indent: 4,
      gapAfter: 2,
    });

    // How it compares (clean plain-language summary)
    pdf.drawTextBlock(`How it compares: ${formatHowItComparesSummary(result)}`, {
      font: "F3",
      fontSize: 9.5,
      lineHeight: 13.5,
      indent: 4,
      gapAfter: 2,
    });

    // Questions you could ask
    if (result.ask_them) {
      pdf.drawTextBlock(`Questions you could ask: "${result.ask_them}"`, {
        font: "F4",
        fontSize: 9.5,
        lineHeight: 13.5,
        indent: 4,
        gapAfter: 2,
      });
    }

    // Sources cited
    if (result.evidence && result.evidence.length > 0) {
      const sourceList = result.evidence
        .map((e) => `[${e.source_title}]`)
        .filter(Boolean)
        .join(" * ");
      if (sourceList) {
        pdf.drawTextBlock(`Sources: ${sourceList}`, {
          font: "F5",
          fontSize: 8.8,
          lineHeight: 12,
          indent: 4,
          colorGray: 0.35,
          gapAfter: 4,
        });
      }
    }

    pdf.drawHorizontalRule(3, 8, 0.4);
  });

  // Section 5: Missing Protections (“Not Found in Your Contract”)
  if (summary?.missing_protections && summary.missing_protections.length > 0) {
    pdf.drawSectionHeading("5. Missing Protections (\"Not Found in Your Contract\")");
    pdf.drawTextBlock(
      "Standard templates for this contract type commonly include the following protective terms, which were not found in your contract text.",
      { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
    );

    summary.missing_protections.forEach((m, idx) => {
      pdf.drawTextBlock(`5.${idx + 1} ${m.title}: ${m.ask_them}`, {
        font: "F3",
        fontSize: 9.8,
        lineHeight: 13.5,
        indent: 6,
        gapAfter: 4,
      });
    });
  }

  // Section 6: Numbered Negotiation Checklist (Exact writing lines from modal)
  const allQuestions: string[] = [];
  const seenQuestions = new Set<string>();
  for (const a of summary?.top_asks ?? []) {
    if (a.question && !seenQuestions.has(a.question)) {
      seenQuestions.add(a.question);
      allQuestions.push(a.question);
    }
  }
  for (const r of allResults) {
    if (r.ask_them && !seenQuestions.has(r.ask_them)) {
      seenQuestions.add(r.ask_them);
      allQuestions.push(r.ask_them);
    }
  }
  for (const m of summary?.missing_protections ?? []) {
    if (m.ask_them && !seenQuestions.has(m.ask_them)) {
      seenQuestions.add(m.ask_them);
      allQuestions.push(m.ask_them);
    }
  }

  if (allQuestions.length > 0) {
    pdf.drawSectionHeading("6. Numbered Negotiation Checklist");
    pdf.drawTextBlock(
      "Use this checklist during meetings with your manager, record label, brand partner, or lawyer. Check each box once discussed and use the lines to record agreed terms.",
      { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
    );

    allQuestions.forEach((q, idx) => {
      pdf.ensureSpace(46);
      pdf.drawTextBlock(`[   ]  ${idx + 1}. "${q}"`, {
        font: "F4",
        fontSize: 9.8,
        lineHeight: 13.5,
        gapAfter: 2,
      });
      pdf.drawTextBlock(
        "       Notes: __________________________________________________________________________________",
        {
          font: "F5",
          fontSize: 8.5,
          lineHeight: 12.5,
          colorGray: 0.35,
          gapAfter: 1,
        },
      );
      pdf.drawTextBlock(
        "       Agreed: _________________________________________________ Date: _______________ Initials: _____",
        {
          font: "F5",
          fontSize: 8.5,
          lineHeight: 12.5,
          colorGray: 0.35,
          gapAfter: 5,
        },
      );
    });
  }

  // Section 7: Reference Standards Cited
  const citedStandards = new Set<string>();
  for (const r of allResults) {
    for (const ev of r.evidence ?? []) {
      if (ev.source_title) citedStandards.add(ev.source_title);
    }
    if (r.standard_template_id) citedStandards.add(r.standard_template_id);
  }

  if (citedStandards.size > 0) {
    pdf.drawSectionHeading("7. Reference Standards Cited");
    pdf.drawTextBlock(
      "Excerpts and comparison norms cited in this evaluation were sourced from the following reviewed public standards:",
      { font: "F3", fontSize: 10, lineHeight: 14, gapAfter: 6 },
    );
    Array.from(citedStandards).forEach((std) => {
      pdf.drawTextBlock(`* ${std}`, {
        font: "F3",
        fontSize: 9.2,
        lineHeight: 13,
        indent: 10,
        gapAfter: 2,
      });
    });
  }

  const modelVersion = summary?.versions.model || "gemini-3.8-flash";
  const corpusVersion = summary?.versions.corpus || "KECOBO/Indie-Standard";

  return pdf.build(
    "Mbiu Contract Evaluation Report * Not Legal Advice * Independent Educational Evaluation",
    `Generated: ${currentDate} * Model: ${modelVersion} * Corpus: ${corpusVersion}`,
  );
}

/**
 * Generates the PDF report and opens it in a new browser tab as a native PDF document
 * (or downloads it directly as a .pdf file if the caller requests direct download or popups are blocked).
 */
export function openEvaluationReportPdf(
  params: ReportPdfParams,
  options: { download?: boolean } = {},
): void {
  if (typeof window === "undefined") return;

  const pdfBytes = generateEvaluationReportPdf(params);
  const blob = new Blob([pdfBytes.buffer as ArrayBuffer], { type: "application/pdf" });
  const blobUrl = URL.createObjectURL(blob);
  const fileName = `Mbiu-Contract-Evaluation-Report-${new Date().toISOString().slice(0, 10)}.pdf`;

  if (options.download) {
    const link = window.document.createElement("a");
    link.href = blobUrl;
    link.download = fileName;
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
    return;
  }

  const opened = window.open(blobUrl, "_blank");
  if (!opened) {
    // Fallback if a strict mobile browser blocks new tabs: trigger PDF file download
    const link = window.document.createElement("a");
    link.href = blobUrl;
    link.download = fileName;
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
  }
  setTimeout(() => URL.revokeObjectURL(blobUrl), 120_000);
}
