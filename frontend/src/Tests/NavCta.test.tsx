import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NavCta } from "@/components/landing/navbar/NavCta";

describe("NavCta Component", () => {
  it("renders upload CTA link with icon", () => {
    const markup = renderToStaticMarkup(<NavCta href="#upload" />);
    expect(markup).toContain('href="#upload"');
    expect(markup).toContain("Upload your contract");
  });
});
