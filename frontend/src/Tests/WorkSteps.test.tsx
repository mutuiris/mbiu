import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { WorkSteps } from "@/components/landing/WorkSteps";

describe("WorkSteps Component", () => {
  it("renders the How it works heading", () => {
    const markup = renderToStaticMarkup(<WorkSteps />);
    expect(markup).toContain("How it works");
  });

  it("renders the default 3 process steps with numbers and text", () => {
    const markup = renderToStaticMarkup(<WorkSteps />);
    expect(markup).toContain("01");
    expect(markup).toContain("Upload");
    expect(markup).toContain("your contract.");
    expect(markup).toContain("02");
    expect(markup).toContain("Understand");
    expect(markup).toContain("each clause.");
    expect(markup).toContain("03");
    expect(markup).toContain("Take your questions");
    expect(markup).toContain("to the table.");
  });

  it("allows custom steps to be passed", () => {
    const custom = [
      { number: "A", title: "First Step", body: "First details." },
      { number: "B", title: "Second Step", body: "Second details." },
    ];
    const markup = renderToStaticMarkup(<WorkSteps steps={custom} />);
    expect(markup).toContain("First Step");
    expect(markup).toContain("Second details.");
    expect(markup).not.toContain("01");
  });
});
