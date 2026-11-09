import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { BrandColumn } from "./BrandColumn";

describe("BrandColumn Component", () => {
  it("renders the brand logo and name linking to home", () => {
    const markup = renderToStaticMarkup(<BrandColumn />);
    expect(markup).toContain('href="/"');
    expect(markup).toContain("mbiu");
    expect(markup).toContain("mbiu-horn.png");
  });

  it("renders the KamiLimu support link", () => {
    const markup = renderToStaticMarkup(<BrandColumn />);
    expect(markup).toContain("Supported by");
    expect(markup).toContain("https://www.kamilimu.org/");
    expect(markup).toContain("KamiLimu");
  });

  it("renders the mission statement and disclaimer", () => {
    const markup = renderToStaticMarkup(<BrandColumn />);
    expect(markup).toContain("A tool that helps Kenyan musicians understand a music contract");
    expect(markup).toContain("Not legal advice.");
  });
});
