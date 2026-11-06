import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { SummaryCard } from "./SummaryCard";
import type { Summary } from "../../lib/api/generated/types.gen";

const summary: Summary = {
  top_asks: [],
  contract_issues: [],
  missing_protections: [
    {
      template_id: "KE-AUDIT",
      title: "Audit",
      excerpt: "The Artist may audit the books once a year.",
      ask_them: "Can we add a clause that lets me check your accounts once a year?",
    },
  ],
  good_news: [],
  matches_count: 2,
  skipped_pages: [],
  ask_list: [],
  versions: { schema_version: "1", prompt: "compare_v1", model: "m", corpus: "v1" },
};

describe("SummaryCard", () => {
  it("lists protections the contract is missing, with the question to ask", () => {
    const html = renderToStaticMarkup(<SummaryCard summary={summary} />);
    expect(html).toContain("Missing from your contract");
    expect(html).toContain("Can we add a clause that lets me check your accounts once a year?");
    expect(html).toContain("Typical clauses:");
  });
});
