import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CardHeader } from "@/components/results/CardHeader";

describe("CardHeader", () => {
  it("renders heading title, status badge and PDF jump link", () => {
    const html = renderToStaticMarkup(
      <CardHeader
        clauseId="c-123"
        headingTitle="Clause 1, Term & Duration"
        badge={{ display: "🟠 Worth inquiry", className: "badge-worth" }}
        topicText="Term & Duration"
        locationLabel="Page 2, clause 1"
        firstPage={2}
      />
    );

    expect(html).toContain("Clause 1, Term &amp; Duration");
    expect(html).toContain("🟠 Worth inquiry");
    expect(html).toContain("Page 2, clause 1");
    expect(html).toContain('aria-label="Jump to page 2 in PDF viewer"');
  });
});
