import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Users, Heart } from "lucide-react";

export const metadata: Metadata = {
  title: "Our Team - Mbiu",
  description: "Meet the team building Mbiu for Kenyan music artists.",
};

export default function TeamPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[840px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
            <Users className="h-3.5 w-3.5" />
            Contributors
          </span>

          <h1 className="mt-3 font-serif text-[1.5rem] font-semibold tracking-[-0.025em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.85rem]">
            Our Team
          </h1>

          <p className="mt-2 text-[0.95rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            The independent team building Mbiu as part of the 2026 Mozilla x KamiLimu Buildathon.
          </p>

          <div className="mt-7 space-y-6 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            <p>
              We are software engineers, researchers, and creators based in Nairobi, Kenya. We build
              open-access technology to protect independent musicians and creative workers.
            </p>

            <div className="rounded-2xl border border-mbiu-ink/10 bg-white/50 p-6 dark:border-white/10 dark:bg-white/[0.04]">
              <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
                Mozilla x KamiLimu Innovation
              </h2>
              <p className="mt-2 text-[0.92rem] text-mbiu-ink/80 dark:text-[#B9C1C5]">
                Developed under the mentorship and sponsorship of KamiLimu Limited and the Mozilla
                Foundation. Built to advance creative rights and fair contract literacy across
                Kenya.
              </p>
            </div>

            <div className="flex items-center gap-2 pt-4 text-[0.9rem] font-medium text-mbiu-ink/70 dark:text-[#9aa5aa]">
              <Heart className="h-4 w-4 text-rose-500" />
              Built for independent artists in Nairobi and across Africa.
            </div>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
