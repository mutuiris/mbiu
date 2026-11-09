import { describe, expect, it } from "vitest";

import { metadata, viewport } from "./layout";

describe("site metadata", () => {
  it("gives shared links a large preview card", () => {
    expect(String(metadata.metadataBase)).toBe("https://mbiu-music.vercel.app/");
    expect(metadata.openGraph).toMatchObject({ type: "website", siteName: "Mbiu" });
    expect(metadata.twitter).toMatchObject({ card: "summary_large_image" });
  });

  it("colours the browser bar like the page", () => {
    expect(viewport.themeColor).toBe("#fcf4e5");
  });
});
