import type { EvaluationEvent } from "./stream";

/**
 * Pre-recorded synthetic evaluation stream events for local frontend development,
 * demos, and offline testing without requiring a live backend.
 */
export const SYNTHETIC_EVALUATION_EVENTS: EvaluationEvent[] = [
  {
    type: "document",
    schema_version: "1",
    payload: {
      page_count: 8,
      sections: [
        { section_id: "sec-1", title: "Grant of Rights", kind: "body" },
        { section_id: "sec-2", title: "Royalties & Accounting", kind: "body" },
        { section_id: "sec-3", title: "Term and Territory", kind: "body" },
        { section_id: "sec-4", title: "General Legal", kind: "body" },
      ],
      clauses: [
        {
          clause_id: "c-1",
          section_id: "sec-1",
          number: "1.1",
          heading: "Master Rights Assignment",
          pages: [1, 2],
          start: 120,
          end: 450,
          text: "The Artist hereby irrevocably sells, assigns, and transfers to the Company all right, title, and interest in and to the Masters, throughout the Universe, in perpetuity.",
        },
        {
          clause_id: "c-2",
          section_id: "sec-2",
          number: "3.2",
          heading: "Mechanical Royalties",
          pages: [3],
          start: 890,
          end: 1200,
          text: "Company shall pay Artist a royalty of 12% of Net Receipts, defined after deduction of all recording costs, marketing, distribution fees, legal fees, packaging charges, and general overhead.",
        },
        {
          clause_id: "c-3",
          section_id: "sec-2",
          number: "4.1",
          heading: "Audit Rights",
          pages: [4],
          start: 1400,
          end: 1650,
          text: "Artist may inspect the books of Company once every two years upon thirty (30) days prior written notice, at Artist's sole expense, provided if an underpayment exceeding 10% is found, Company shall reimburse the reasonable audit fee.",
        },
        {
          clause_id: "c-4",
          section_id: "sec-3",
          number: "5.1",
          heading: "Initial Term",
          pages: [5],
          start: 1800,
          end: 1980,
          text: "The Initial Contract Period shall begin on the date hereof and continue for a period of one (1) year following commercial delivery of the first Album.",
        },
        {
          clause_id: "c-5",
          section_id: "sec-4",
          number: "9.4",
          heading: "Governing Law",
          pages: [7],
          start: 2400,
          end: 2520,
          text: "This Agreement shall be construed and enforced in accordance with the Laws of Kenya, and the parties submit to the exclusive jurisdiction of the Courts of Nairobi.",
        },
        {
          clause_id: "c-6",
          section_id: "sec-4",
          number: "10.2",
          heading: "Severability",
          pages: [8],
          start: 2700,
          end: 2810,
          text: "If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.",
        },
      ],
      skipped_pages: [],
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 1,
      total: 6,
    },
  },
  {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: "c-1",
      status: "evaluated",
      comparison: "worse_for_you",
      headline: "You give up ownership of your master recordings forever",
      what_it_says:
        "The Artist hereby irrevocably sells, assigns, and transfers to the Company all right, title, and interest in and to the Masters, throughout the Universe, in perpetuity.",
      what_it_means:
        "Even after your contract ends or the label recoups its money, the label owns your masters forever. You cannot license them or take them elsewhere.",
      original_text:
        "The Artist hereby irrevocably sells, assigns, and transfers to the Company all right, title, and interest in and to the Masters, throughout the Universe, in perpetuity.",
      pages: [1, 2],
      linked_clauses: [],
      evidence: [
        {
          evidence_id: "ev-1",
          template_id: "std-rec-kenya-2024",
          source_title: "Reviewed Standard Recording Agreement Kenya",
          jurisdiction: "Kenya",
          excerpt:
            "Artist retains ownership of masters, licensing them exclusively to the Label for a term not exceeding 7 years from commercial release.",
        },
      ],
      evidence_ids: ["ev-1"],
      comparison_note: "Perpetual assignment vs standard 7-year exclusive license.",
      evidence_quote: "Artist retains ownership of masters, licensing them exclusively to the Label",
      fairer_wording:
        "Artist grants Company an exclusive license to exploit the Masters for a term of five (5) years from release, after which all rights revert to Artist.",
      standard_excerpt:
        "Artist retains ownership of masters, licensing them exclusively to the Label for a term not exceeding 7 years.",
      standard_template_id: "std-rec-kenya-2024",
      ask_them:
        "Can we replace the perpetual master transfer with an exclusive 5-year license that reverts back to me?",
      impact_inputs: null,
      provider: "gemini",
      model_version: "gemini-3.8-flash",
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 2,
      total: 6,
    },
  },
  {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: "c-2",
      status: "evaluated",
      comparison: "worse_for_you",
      headline: "Uncapped deductions can swallow almost all your streaming royalties",
      what_it_says:
        "Company shall pay Artist a royalty of 12% of Net Receipts, defined after deduction of all recording costs, marketing, distribution fees, legal fees, packaging charges, and general overhead.",
      what_it_means:
        "12% on 'Net' after marketing and general overhead means the company can deduct almost all revenue before paying you anything.",
      original_text:
        "Company shall pay Artist a royalty of 12% of Net Receipts, defined after deduction of all recording costs, marketing, distribution fees, legal fees, packaging charges, and general overhead.",
      pages: [3],
      linked_clauses: [],
      evidence: [],
      evidence_ids: [],
      comparison_note: null,
      evidence_quote: null,
      fairer_wording:
        "Company shall pay Artist a minimum 20% royalty based on gross receipts, with deductions capped strictly at verifiable third-party distribution fees.",
      standard_excerpt: "Standard indie royalty is 18-25% on net receipts with capped deductions.",
      standard_template_id: "std-rec-kenya-2024",
      ask_them:
        "Can we remove general overhead from deductions and cap marketing recoupment at 50%?",
      impact_inputs: null,
      provider: "gemini",
      model_version: "gemini-3.8-flash",
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 3,
      total: 6,
    },
  },
  {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: "c-3",
      status: "evaluated",
      comparison: "better_for_you",
      headline: "You have a clear right to audit with fee reimbursement",
      what_it_says:
        "Artist may inspect the books of Company once every two years upon thirty (30) days prior written notice, at Artist's sole expense, provided if an underpayment exceeding 10% is found, Company shall reimburse the reasonable audit fee.",
      what_it_means:
        "If you suspect royalty accounting mistakes, you can hire an accountant. If they owe you >10% more, they pay for the audit.",
      original_text:
        "Artist may inspect the books of Company once every two years upon thirty (30) days prior written notice, at Artist's sole expense, provided if an underpayment exceeding 10% is found, Company shall reimburse the reasonable audit fee.",
      pages: [4],
      linked_clauses: [],
      evidence: [],
      evidence_ids: [],
      comparison_note: null,
      evidence_quote: null,
      fairer_wording: null,
      standard_excerpt: "Standard clauses require the label to pay audit fees on 10% underpayment.",
      standard_template_id: "std-rec-kenya-2024",
      ask_them: null,
      impact_inputs: null,
      provider: "gemini",
      model_version: "gemini-3.8-flash",
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 4,
      total: 6,
    },
  },
  {
    type: "clause_failed",
    schema_version: "1",
    payload: {
      clause_id: "c-4",
      reason: "timeout",
      retryable: true,
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 5,
      total: 6,
    },
  },
  {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: "c-5",
      status: "evaluated",
      comparison: "matches_standard",
      headline: "Governing law in Nairobi, Kenya",
      what_it_says:
        "This Agreement shall be construed and enforced in accordance with the Laws of Kenya, and the parties submit to the exclusive jurisdiction of the Courts of Nairobi.",
      what_it_means: "Any legal disputes will be handled in Kenya under Kenyan courts.",
      original_text:
        "This Agreement shall be construed and enforced in accordance with the Laws of Kenya, and the parties submit to the exclusive jurisdiction of the Courts of Nairobi.",
      pages: [7],
      linked_clauses: [],
      evidence: [],
      evidence_ids: [],
      comparison_note: null,
      evidence_quote: null,
      fairer_wording: null,
      standard_excerpt: "Standard Kenyan governing law clause.",
      standard_template_id: "std-rec-kenya-2024",
      ask_them: null,
      impact_inputs: null,
      provider: "gemini",
      model_version: "gemini-3.8-flash",
    },
  },
  {
    type: "progress",
    schema_version: "1",
    payload: {
      stage: "compare",
      done: 6,
      total: 6,
    },
  },
  {
    type: "clause_result",
    schema_version: "1",
    payload: {
      clause_id: "c-6",
      status: "evaluated",
      comparison: "matches_standard",
      headline: "Standard severability protection",
      what_it_says:
        "If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.",
      what_it_means: "One illegal sentence won't cancel the entire contract.",
      original_text:
        "If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.",
      pages: [8],
      linked_clauses: [],
      evidence: [],
      evidence_ids: [],
      comparison_note: null,
      evidence_quote: null,
      fairer_wording: null,
      standard_excerpt: "Standard severability clause.",
      standard_template_id: "std-rec-kenya-2024",
      ask_them: null,
      impact_inputs: null,
      provider: "gemini",
      model_version: "gemini-3.8-flash",
    },
  },
  {
    type: "done",
    schema_version: "1",
    payload: {
      versions: {
        corpus: "1.0",
        model: "gemini-3.8-flash",
        prompt: "1.0",
        schema_version: "1",
      },
      matches_count: 2,
      top_asks: [
        {
          clause_id: "c-1",
          question:
            "Can we replace the perpetual master transfer with an exclusive 5-year license that reverts back to me?",
        },
        {
          clause_id: "c-2",
          question:
            "Can we remove general overhead from deductions and cap marketing recoupment at 50%?",
        },
      ],
      ask_list: [
        {
          clause_id: "c-1",
          question:
            "Can we replace the perpetual master transfer with an exclusive 5-year license that reverts back to me?",
        },
        {
          clause_id: "c-2",
          question:
            "Can we remove general overhead from deductions and cap marketing recoupment at 50%?",
        },
      ],
      good_news: [
        {
          clause_id: "c-3",
          text: "You have a solid audit clause with expenses reimbursed if they owe you >10%.",
        },
      ],
      contract_issues: [],
      missing_protections: [],
      skipped_pages: [],
    },
  },
];

/**
 * Creates an async generator emitting the synthetic stream events with
 * simulated realistic delays.
 */
export async function* createSyntheticEventStream(
  delayMs: number = 300
): AsyncGenerator<EvaluationEvent, void, unknown> {
  for (const event of SYNTHETIC_EVALUATION_EVENTS) {
    if (delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    yield event;
  }
}
