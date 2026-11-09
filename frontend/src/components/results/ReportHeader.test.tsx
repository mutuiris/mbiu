import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ReportHeader, type ReportHeaderProps } from "./ReportHeader";

const base: ReportHeaderProps = {
  documentTitle: "Exclusive 360-degree recording agreement",
  pageCount: 11,
  checked: 24,
  total: 127,
  isStreaming: false,
  counts: { typical: 0, unusual: 15, worth_asking_about: 0, cannot_compare: 9 },
  notChecked: 103,
  onCheckRest: () => {},
  onDownload: () => {},
  onCheckAnother: () => {},
  keep: null,
};
const render = (props: Partial<ReportHeaderProps> = {}) =>
  renderToStaticMarkup(<ReportHeader {...base} {...props} />);

describe("ReportHeader", () => {
  it("says what was done when checking has finished", () => {
    const html = render();
    expect(html).toContain("Your contract report");
    expect(html).toContain("Done. Checked the 24 most important clauses.");
    expect(html).toContain("Check the other 103");
    expect(html).toContain("Download report (PDF)");
    expect(html).toContain("Check another contract");
  });

  it("shows live progress while checking", () => {
    const html = render({ isStreaming: true, checked: 10 });
    expect(html).toContain("Checking… 10 of 127");
    expect(html).not.toContain("Done.");
  });

  it("shows the four outcome counts with the approved labels", () => {
    const html = render();
    for (const label of ["Worth inquiry", "Unusual", "Typical", "Couldn&#x27;t compare"]) {
      expect(html).toContain(label);
    }
    expect(html).toContain(">15<");
    expect(html).toContain(">9<");
  });

  it("offers no extra check when every clause was checked", () => {
    expect(render({ notChecked: 0, checked: 127 })).not.toContain("Check the other");
  });

  it("uses one clause in the singular", () => {
    expect(render({ checked: 1 })).toContain("Checked the 1 most important clause.");
  });
});
