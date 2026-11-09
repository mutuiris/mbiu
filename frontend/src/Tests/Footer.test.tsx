import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Footer } from "@/components/footer/Footer";

describe("Footer Component", () => {
  it("renders the brand logo and name", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("mbiu");
    expect(markup).toContain("mbiu-horn.png");
  });

  it("renders the KamiLimu support acknowledgment", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("KamiLimu");
    expect(markup).toContain("Supported by");
  });

  it("renders plain-language explanation and disclaimer", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain(
      "A tool that helps Kenyan musicians understand a music contract before they sign"
    );
    expect(markup).toContain("Not legal advice.");
  });

  it("renders navigation columns with working routes: Platform and Privacy & Legal", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("Platform");
    expect(markup).toContain("Privacy &amp; Legal");
    expect(markup).toContain('href="/"');
    expect(markup).toContain('href="/#how-it-works"');
    expect(markup).toContain('href="/#about"');
    expect(markup).toContain('href="/#upload"');
    expect(markup).toContain('href="/team"');
    expect(markup).toContain('href="/privacy"');
    expect(markup).toContain('href="/terms"');
  });

  it("renders centered copyright notice and omits old project subtitle", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("© 2026 Mbiu. All rights reserved.");
    expect(markup).not.toContain("Kenya Music Contract Project");
  });
});
