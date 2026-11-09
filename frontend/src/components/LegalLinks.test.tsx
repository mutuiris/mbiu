import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { LegalLinks } from "./LegalLinks";

describe("LegalLinks Component", () => {
  it("renders the Privacy & Legal heading", () => {
    const markup = renderToStaticMarkup(<LegalLinks />);
    expect(markup).toContain("Privacy &amp; Legal");
  });

  it("renders privacy policy and terms links", () => {
    const markup = renderToStaticMarkup(<LegalLinks />);
    expect(markup).toContain('href="/privacy"');
    expect(markup).toContain("Privacy Policy");
    expect(markup).toContain('href="/terms"');
    expect(markup).toContain("Terms of Service");
  });
});
