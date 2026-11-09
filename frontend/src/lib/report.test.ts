import { describe, expect, it } from "vitest";

import type { ClauseResult } from "./api/generated/types.gen";
import { cleanReferenceText, displayNumber, groupResults, mergeAsks, readableClauseName } from "./report";

describe("mergeAsks", () => {
  it("merges the reworded 15% free-goods questions from the 04 contract", () => {
    const merged = mergeAsks([
      {
        clause_id: "1.8",
        question:
          "Could we remove the 15% free goods deduction on digital streams, downloads, and ringtones?",
      },
      { clause_id: "1.12(b)", question: "Could we remove the Free Goods Allowance of fifteen percent (15%)?" },
      { clause_id: "5", question: "Can we agree that recording costs are not fully taken from my earnings?" },
    ]);
    expect(merged).toEqual([
      {
        question:
          "Could we remove the 15% free goods deduction on digital streams, downloads, and ringtones?",
        clauseIds: ["1.8", "1.12(b)"],
      },
      {
        question: "Can we agree that recording costs are not fully taken from my earnings?",
        clauseIds: ["5"],
      },
    ]);
  });

  it("keeps questions apart when their numbers differ", () => {
    expect(
      mergeAsks([
        { clause_id: "a", question: "Could we lower the 20% management commission?" },
        { clause_id: "b", question: "Could we lower the 25% management commission?" },
      ]),
    ).toHaveLength(2);
  });

  it("drops exact duplicates and null clause ids", () => {
    expect(
      mergeAsks([
        { clause_id: null, question: "Q?" },
        { clause_id: "2", question: "q?" },
      ]),
    ).toEqual([{ question: "Q?", clauseIds: ["2"] }]);
  });

  it("returns nothing for no questions", () => {
    expect(mergeAsks([])).toEqual([]);
  });
});

describe("displayNumber", () => {
  it("keeps real clause numbering", () => {
    for (const n of ["1", "4.1", "1.12(b)", "5.3(d)", "(b)", "22", "7A"]) expect(displayNumber(n)).toBe(n);
  });
  it("drops the internal slugs the backend uses for unnumbered clauses", () => {
    for (const n of ["preamble", "management_and_ancillary_rights_agreement", "1_2", "7.2_2", "schedule_2_irrevocable_mandate_to_cmos_mcsk_kamp_prisk_a_3", "recitals", "", null, undefined]) {
      expect(displayNumber(n)).toBeNull();
    }
  });
});

describe("readableClauseName", () => {
  it("never prints a slug as a clause number (04 contract)", () => {
    expect(readableClauseName({ number: "1_2", heading: "DEFINITIONS AND CONSTRUCTION" })).toBe("DEFINITIONS AND CONSTRUCTION");
    expect(readableClauseName({ number: "preamble", heading: null, text: "EXCLUSIVE 360-DEGREE RECORDING, CO-PUBLISHING, PERSONAL MANAGEMENT" })).toBe(
      "EXCLUSIVE 360-DEGREE RECORDING, CO-PUBLISHING, PERSONAL MANAGEMENT",
    );
    expect(readableClauseName({ number: "7.2_2", heading: null, text: "Clause 7.2, or Clause 9.1, or any other provision" })).not.toContain("7.2_2");
  });

  it("names clauses for artists, never by their internal id", () => {
    expect(readableClauseName({ number: "4.1", heading: "Gross Fee" })).toBe(
      "Clause 4.1 · Gross Fee",
    );
    expect(
      readableClauseName(
        { number: "1", heading: null, text: "The Brand shall pay the Artist within thirty days of invoice." },
      ),
    ).toBe("Clause 1 · The Brand shall pay the Artist…");
    expect(readableClauseName({ number: null, heading: "Recitals" })).toBe("Recitals");
    expect(readableClauseName(undefined)).toBe(
      "A clause in your contract",
    );
  });

  it("doesn't repeat the clause number from the clause text", () => {
    expect(readableClauseName({ number: "1.1", heading: null, text: '1.1 "Advance" means any sum paid by Company to Artist' })).toBe(
      'Clause 1.1 · "Advance" means any sum paid by…',
    );
    expect(readableClauseName({ number: "1.12(b)", heading: null, text: "(b) the Free Goods Allowance of fifteen percent" })).toBe(
      "Clause 1.12(b) · the Free Goods Allowance of fifteen…",
    );
  });

  it("uses the number alone when there is no heading or text", () => {
    expect(readableClauseName({ number: "7.2", heading: null, text: null })).toBe("Clause 7.2");
  });
});

describe("cleanReferenceText", () => {
  it("cleans blank template forms out of reference text", () => {
    expect(
      cleanReferenceText(
        "## RECORDING/PRODUCER AGREEMENT This license agreement is made this …………….. day of ………20…. between",
      ),
    ).toBe("RECORDING/PRODUCER AGREEMENT This license agreement is made this day of 20 between");
    expect(cleanReferenceText("Royalties are paid **quarterly**.")).toBe("Royalties are paid quarterly.");
  });
});

describe("groupResults", () => {
  const result = (clause_id: string, comparison: ClauseResult["comparison"], pages = [1]): ClauseResult => ({
    clause_id,
    comparison,
    status: "evaluated",
    headline: "h",
    what_it_says: "s",
    what_it_means: "m",
    original_text: "Notices shall be sent by email.",
    pages,
    linked_clauses: [],
    evidence: [],
    evidence_ids: [],
    comparison_note: null,
    evidence_quote: null,
    standard_excerpt: null,
    standard_template_id: null,
    ask_them: null,
    impact_inputs: null,
    provider: "gemini",
    model_version: "m",
  });
  const lookup = new Map([
    ["notice", { heading: "Notices" }],
    ["unusual-1", { heading: "Free goods" }],
    ["unusual-2", { heading: "Cross-collateralization" }],
    ["cannot", { heading: "Notices" }],
    ["worth", { heading: "Term" }],
  ]);
  const results = [
    result("notice", "matches_standard"),
    result("unusual-2", "not_in_standard", [4]),
    result("cannot", "cannot_compare"),
    result("unusual-1", "not_in_standard", [2]),
    result("worth", "worse_for_you", [3]),
  ];

  it("puts findings on cards in impact order", () => {
    const g = groupResults(results, lookup, new Set());
    expect(g.cards.map((r) => r.clause_id)).toEqual(["worth", "unusual-1", "unusual-2"]);
  });

  it("folds standard clauses and never files couldn't-compare under standard", () => {
    const g = groupResults(results, lookup, new Set());
    expect(g.standard.map((r) => r.clause_id)).toEqual(["notice"]);
    expect(g.cannotCompare.map((r) => r.clause_id)).toEqual(["cannot"]);
  });

  it("counts every checked result by outcome", () => {
    expect(groupResults(results, lookup, new Set()).counts).toEqual({
      typical: 1,
      unusual: 2,
      worth_asking_about: 1,
      cannot_compare: 1,
    });
  });

  it("keeps important couldn't-compare clauses in the PDF write-ups", () => {
    const royalty = { ...result("royalty", "cannot_compare"), original_text: "The Artist's royalty is 12% of net receipts." };
    const g = groupResults([...results, royalty], new Map([...lookup, ["royalty", { heading: "Royalties" }]]), new Set());
    expect(g.writeUps.map((r) => r.clause_id)).toContain("royalty");
    expect(g.writeUps.map((r) => r.clause_id)).not.toContain("cannot");
    expect(g.writeUps.slice(0, 3).map((r) => r.clause_id)).toEqual(["worth", "unusual-1", "unusual-2"]);
  });

  it("gives a card to a standard clause caught up in a clash", () => {
    expect(groupResults(results, lookup, new Set(["notice"])).cards.map((r) => r.clause_id)).toContain("notice");
  });
});
