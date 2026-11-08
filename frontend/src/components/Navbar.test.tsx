import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Navbar } from "./Navbar";

describe("Navbar Component", () => {
  it("renders the brand logo and name", () => {
    const markup = renderToStaticMarkup(<Navbar />);
    expect(markup).toContain("mbiu");
    expect(markup).toContain("mbiu-horn.png");
  });

  it("renders navigation links to the key page sections", () => {
    const markup = renderToStaticMarkup(<Navbar />);
    expect(markup).toContain('href="#how-it-works"');
    expect(markup).toContain('href="/privacy"');
    expect(markup).toContain('href="#about"');
    expect(markup).toContain('href="#upload"');
  });

  it("renders the hamburger menu button for mobile screens with accessibility attributes", () => {
    const markup = renderToStaticMarkup(<Navbar />);
    expect(markup).toContain('aria-label="Open navigation menu"');
    expect(markup).toContain('aria-expanded="false"');
  });

  it("renders the ThemeToggle button", () => {
    const markup = renderToStaticMarkup(<Navbar />);
    expect(markup).toContain("Switch between light and dark mode");
  });
});
