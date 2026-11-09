import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PreviewCard } from "@/components/landing/hero/PreviewCard";

describe("PreviewCard Component", () => {
  it("renders clause title and badge", () => {
    const markup = renderToStaticMarkup(<PreviewCard />);
    expect(markup).toContain("Clause 7.2");
    expect(markup).toContain("Post-term exclusivity");
    expect(markup).toContain("Worth inquiry");
  });

  it("renders sample quote, question, and legal disclaimer", () => {
    const markup = renderToStaticMarkup(<PreviewCard />);
    expect(markup).toContain("Your agreement could restrict you from working with other labels");
    expect(markup).toContain("Could this affect your next opportunity?");
    expect(markup).toContain("This isn&#x27;t legal advice.");
  });
});
