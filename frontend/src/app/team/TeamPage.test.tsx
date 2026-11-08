import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import TeamPage from "./page";

describe("TeamPage", () => {
  it("renders the page title and subtitle", () => {
    const html = renderToStaticMarkup(<TeamPage />);
    expect(html).toContain("Our Team");
    expect(html).toContain("The independent developers and civic researchers behind Mbiu.");
  });

  it("renders all four team members with their roles and bios", () => {
    const html = renderToStaticMarkup(<TeamPage />);

    expect(html).toContain("Steve Wanangwe");
    expect(html).toContain("Backend developer");
    expect(html).toContain("steve.png");

    expect(html).toContain("Bernadette Karanja");
    expect(html).toContain("Frontend developer &amp; Research lead");
    expect(html).toContain("bernadette.png");

    expect(html).toContain("Addy Mutuiri");
    expect(html).toContain("Project lead &amp; AI engineer");
    expect(html).toContain("addy.png");

    expect(html).toContain("Mercyline Nyaboke");
    expect(html).toContain("Frontend &amp; Accessibility developer");
    expect(html).toContain("mercyline.png");
  });

  it("renders social links and contact emails", () => {
    const html = renderToStaticMarkup(<TeamPage />);
    expect(html).toContain("mailto:stevewanash1@gmail.com");
    expect(html).toContain("mailto:benadettekaranja@gmail.com");
    expect(html).toContain("mailto:muneneaddy@gmail.com");
    expect(html).toContain("mailto:mercylinenyaboke08@gmail.com");
  });

  it("renders KamiLimu and Mozilla innovation note", () => {
    const html = renderToStaticMarkup(<TeamPage />);
    expect(html).toContain("Mozilla x KamiLimu Innovation");
    expect(html).toContain("https://www.kamilimu.org/");
  });
});
