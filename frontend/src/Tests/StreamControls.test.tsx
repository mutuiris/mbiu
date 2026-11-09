import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StreamControls } from "@/components/landing/stream/StreamControls";

describe("StreamControls Component", () => {
  it("renders the restart button", () => {
    const markup = renderToStaticMarkup(<StreamControls onStartOver={vi.fn()} />);
    expect(markup).toContain("Check another contract");
    expect(markup).toContain("restart-btn");
  });
});
