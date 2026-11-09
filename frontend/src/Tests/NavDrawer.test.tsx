import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NavDrawer } from "@/components/landing/navbar/NavDrawer";

describe("NavDrawer Component", () => {
  it("renders nothing when closed", () => {
    const markup = renderToStaticMarkup(
      <NavDrawer isOpen={false} onClose={vi.fn()} resolveHref={(t) => t} />
    );
    expect(markup).toBe("");
  });

  it("renders mobile drawer panel when open", () => {
    const markup = renderToStaticMarkup(
      <NavDrawer isOpen={true} onClose={vi.fn()} resolveHref={(t) => t} />
    );
    expect(markup).toContain('aria-label="Mobile Navigation"');
    expect(markup).toContain("Close navigation menu");
    expect(markup).toContain("Home");
    expect(markup).toContain("How it works");
    expect(markup).toContain("Privacy");
    expect(markup).toContain("Upload your contract");
  });
});
