import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CopyButton } from "@/components/results/CopyButton";

describe("CopyButton", () => {
  it("renders with default label and aria-label", () => {
    const html = renderToStaticMarkup(<CopyButton text="Test clause text" />);
    expect(html).toContain("📋 Copy");
    expect(html).toContain('aria-label="Copy to clipboard"');
  });

  it("renders with custom label and className", () => {
    const html = renderToStaticMarkup(
      <CopyButton
        text="Sample"
        label="Copy Text"
        className="custom-copy-btn"
      />
    );
    expect(html).toContain("Copy Text");
    expect(html).toContain("custom-copy-btn");
  });
});
