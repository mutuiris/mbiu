import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { HeroContent } from "@/components/landing/hero/HeroContent";

describe("HeroContent Component", () => {
  it("renders main headline and core value proposition", () => {
    const markup = renderToStaticMarkup(<HeroContent />);
    expect(markup).toContain("Understand your contract before you sign it.");
    expect(markup).toContain("Your music. Your rights. Your decisions.");
    expect(markup).toContain("Upload your music contract and understand what you&#x27;re agreeing to");
  });

  it("renders upload CTA link pointing to upload section", () => {
    const markup = renderToStaticMarkup(<HeroContent uploadHref="#upload" />);
    expect(markup).toContain('href="#upload"');
    expect(markup).toContain("Upload your contract");
  });

  it("renders zero-storage privacy notice", () => {
    const markup = renderToStaticMarkup(<HeroContent />);
    expect(markup).toContain("Mbiu does not store your contracts on our servers.");
  });
});
