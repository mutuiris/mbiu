import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { QuestionsToAsk } from "./QuestionsToAsk";

const asks04 = [
  {
    clause_id: "1.8",
    question: "Could we remove the 15% free goods deduction on digital streams, downloads, and ringtones?",
  },
  { clause_id: "1.12(b)", question: "Could we remove the Free Goods Allowance of fifteen percent (15%)?" },
  { clause_id: "5", question: "Can we agree that recording costs are not fully taken from my earnings?" },
];
const lookup = new Map([
  ["1.8", { number: "1.8", heading: null, pages: [2] }],
  ["1.12(b)", { number: "1.12(b)", heading: null, pages: [2] }],
  ["5", { number: "5", heading: "Recording costs", pages: [4] }],
]);

describe("QuestionsToAsk", () => {
  it("merges repeated questions and names every clause", () => {
    const html = renderToStaticMarkup(<QuestionsToAsk asks={asks04} clauseLookup={lookup} onView={() => {}} />);
    expect(html).toContain("Questions to ask before you sign");
    expect(html.match(/<li/g)).toHaveLength(2);
    expect(html).toContain("Clause 1.8 and 1.12(b)");
    expect(html).toContain("Page 2");
    expect(html).toContain("Copy all");
  });

  it("never puts quote marks around a question", () => {
    const html = renderToStaticMarkup(<QuestionsToAsk asks={asks04} clauseLookup={lookup} onView={() => {}} />);
    expect(html).not.toMatch(/[“"]Could/);
  });

  it("never shows a slug clause number in the source line", () => {
    const html = renderToStaticMarkup(
      <QuestionsToAsk
        asks={[{ clause_id: "x", question: "Can we change the definitions?" }]}
        clauseLookup={new Map([["x", { number: "1_2", heading: "Definitions", pages: [1] }]])}
        onView={() => {}}
      />,
    );
    expect(html).not.toContain("1_2");
    expect(html).toContain("Page 1");
  });

  it("renders nothing without questions", () => {
    expect(renderToStaticMarkup(<QuestionsToAsk asks={[]} clauseLookup={lookup} onView={() => {}} />)).toBe("");
  });
});
