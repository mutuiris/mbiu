import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CardQuestions } from "@/components/results/CardQuestions";

describe("CardQuestions", () => {
  it("renders nothing when askThem is null or undefined", () => {
    const htmlNull = renderToStaticMarkup(<CardQuestions whatsappShareUrl="" />);
    expect(htmlNull).toBe("");
  });

  it("renders questions, copy button, and WhatsApp share link when present", () => {
    const html = renderToStaticMarkup(
      <CardQuestions
        askThem="Can we shorten the audit timeframe to 30 days?"
        whatsappShareUrl="https://wa.me/?text=audit"
      />
    );

    expect(html).toContain("Questions you could ask");
    expect(html).toContain("Can we shorten the audit timeframe to 30 days?");
    expect(html).toContain("WhatsApp");
    expect(html).toContain('href="https://wa.me/?text=audit"');
  });
});
