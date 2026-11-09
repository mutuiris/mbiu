import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NavLinks, DEFAULT_NAV_LINKS } from "@/components/landing/navbar/NavLinks";

describe("NavLinks Component", () => {
  it("renders all default navigation links", () => {
    const markup = renderToStaticMarkup(
      <NavLinks resolveHref={(target) => target} />
    );
    for (const link of DEFAULT_NAV_LINKS) {
      expect(markup).toContain(link.label);
      expect(markup).toContain(`href="${link.href}"`);
    }
  });
});
