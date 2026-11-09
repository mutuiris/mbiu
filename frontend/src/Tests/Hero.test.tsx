import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Hero } from "@/components/landing/hero/Hero";

describe("Hero Component", () => {
  it("renders both hero text content and preview card in grid", () => {
    const markup = renderToStaticMarkup(<Hero />);
    expect(markup).toContain("Understand your contract before you sign it.");
    expect(markup).toContain("Clause 7.2");
    expect(markup).toContain("Post-term exclusivity");
    expect(markup).toContain('id="about"');
  });

  it("supports custom id and className", () => {
    const markup = renderToStaticMarkup(<Hero id="custom-hero" className="test-class" />);
    expect(markup).toContain('id="custom-hero"');
    expect(markup).toContain("test-class");
  });
});
