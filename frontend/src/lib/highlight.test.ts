import { describe, expect, it } from "vitest";
import { escapeHtml, highlightedItems, pagePosition } from "./highlight";

const CLAUSE =
  "7.2 Royalties. The Label shall pay the Artist a royalty of 12% of net receipts after deducting all recording, marketing and video costs.";

describe("highlightedItems", () => {
  it("marks only the clause's items on a single page", () => {
    const items = [
      "7.1 Term. The term is two years.",
      "7.2 Royalties. The Label shall pay the Artist a royalty of 12% of net",
      "receipts after deducting all recording, marketing and video costs.",
      "7.3 Accounting. Statements are sent twice a year.",
    ];
    expect([...highlightedItems(items, CLAUSE, "only")]).toEqual([1, 2]);
  });

  it("matches when pdf.js splits words and drops spaces between items", () => {
    const items = ["7.2 Roy", "alties.The Label shall pay the Artist a royalty of 12%", "of net receipts after deducting all recording, marketing and video costs."];
    expect([...highlightedItems(items, CLAUSE, "only")]).toEqual([0, 1, 2]);
  });

  it("highlights from the start on the first page and up to the end on the last page", () => {
    const first = ["6.9 Notices are in writing.", "7.2 Royalties. The Label shall pay the Artist a royalty of 12% of net"];
    const last = ["receipts after deducting all recording, marketing and video costs.", "7.3 Accounting."];
    expect([...highlightedItems(first, CLAUSE, "first")]).toEqual([1]);
    expect([...highlightedItems(last, CLAUSE, "last")]).toEqual([0]);
    expect([...highlightedItems(["any text", "more"], CLAUSE, "middle")]).toEqual([0, 1]);
  });

  it("marks nothing when the clause is not on the page", () => {
    expect(highlightedItems(["Something else entirely."], CLAUSE, "only").size).toBe(0);
    expect(highlightedItems(["text"], "", "only").size).toBe(0);
  });
});

describe("pagePosition", () => {
  it("places a page within the clause's pages", () => {
    expect(pagePosition(4, [4])).toBe("only");
    expect(pagePosition(4, [5, 4, 6])).toBe("first");
    expect(pagePosition(5, [4, 5, 6])).toBe("middle");
    expect(pagePosition(6, [4, 5, 6])).toBe("last");
    expect(pagePosition(2, [4, 5])).toBeNull();
  });
});

describe("escapeHtml", () => {
  it("escapes text from the PDF before it becomes HTML", () => {
    expect(escapeHtml(`<img src=x onerror="alert('x')">&`)).toBe(
      "&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt;&amp;",
    );
  });
});
