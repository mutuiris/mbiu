import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { Button, Fold, OutcomePill, ReportCard } from "./ui";

describe("report building blocks", () => {
  it("labels outcomes with the approved words and never wraps them", () => {
    const html = renderToStaticMarkup(<OutcomePill comparison="worse_for_you" />);
    expect(html).toContain("Worth inquiry");
    expect(html).toContain("whitespace-nowrap");
  });

  it("makes buttons big enough to tap", () => {
    const html = renderToStaticMarkup(<Button variant="primary">Download report (PDF)</Button>);
    expect(html).toContain("min-h-11");
    expect(html).toContain('type="button"');
  });

  it("shows a fold's summary while it is closed", () => {
    const html = renderToStaticMarkup(<Fold summary="See the exact words">hidden text</Fold>);
    expect(html).toContain("See the exact words");
  });

  it("renders a card as the element asked for", () => {
    expect(renderToStaticMarkup(<ReportCard as="article">x</ReportCard>)).toMatch(/^<article/);
  });
});
