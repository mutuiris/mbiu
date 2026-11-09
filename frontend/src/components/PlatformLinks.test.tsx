import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PlatformLinks } from "./PlatformLinks";

describe("PlatformLinks Component", () => {
  it("renders the Platform heading", () => {
    const markup = renderToStaticMarkup(<PlatformLinks />);
    expect(markup).toContain("Platform");
  });

  it("renders all expected platform links", () => {
    const markup = renderToStaticMarkup(<PlatformLinks />);
    expect(markup).toContain('href="/"');
    expect(markup).toContain('href="/#how-it-works"');
    expect(markup).toContain('href="/#about"');
    expect(markup).toContain('href="/#upload"');
    expect(markup).toContain('href="/team"');
    expect(markup).toContain("Upload Contract");
    expect(markup).toContain("Our Team");
  });
});
