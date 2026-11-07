import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Footer } from "./Footer";

describe("Footer Component", () => {
  it("renders the brand logo and name", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("Mbiu");
    expect(markup).toContain("mbiu-horn.png");
  });

  it("renders the KamiLimu and Mozilla Buildathon acknowledgments", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("KamiLimu");
    expect(markup).toContain("Mozilla");
    expect(markup).toContain("Mozilla Foundation");
  });

  it("renders legal disclaimer and short concise guidance", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("Independent Creator Resource:");
    expect(markup).toContain("It is not a law firm.");
    expect(markup).toContain("It does not provide legal advice.");
  });

  it("renders navigation columns: Platform, About, and Privacy & Legal", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("Platform");
    expect(markup).toContain("About");
    expect(markup).toContain("Privacy &amp; Legal");
    expect(markup).toContain('href="#how-it-works"');
    expect(markup).toContain('href="#upload"');
    expect(markup).toContain('href="#privacy"');
  });

  it("renders copyright and Kenya Music Contract Project note in bottom bar", () => {
    const markup = renderToStaticMarkup(<Footer />);
    expect(markup).toContain("© 2026 Mbiu. All rights reserved.");
    expect(markup).toContain("Kenya Music Contract Project");
  });
});
