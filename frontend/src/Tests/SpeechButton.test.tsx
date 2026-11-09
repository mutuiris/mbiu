import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { SpeechButton, ReadAloudButton } from "@/components/results/SpeechButton";

describe("SpeechButton", () => {
  it("renders with read aloud label and speaker icon", () => {
    const html = renderToStaticMarkup(<SpeechButton text="Read this aloud" />);
    expect(html).toContain("Read aloud");
    expect(html).toContain("🔊");
    expect(html).toContain('aria-label="Read card summary aloud"');
  });

  it("exports ReadAloudButton as alias", () => {
    expect(ReadAloudButton).toBe(SpeechButton);
  });
});
