import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NavBrand } from "@/components/landing/navbar/NavBrand";

describe("NavBrand Component", () => {
  it("renders the brand horn icon and logo text", () => {
    const markup = renderToStaticMarkup(<NavBrand href="/" />);
    expect(markup).toContain('href="/"');
    expect(markup).toContain("mbiu");
    expect(markup).toContain("mbiu-horn.png");
    expect(markup).toContain('aria-label="Mbiu home"');
  });
});
