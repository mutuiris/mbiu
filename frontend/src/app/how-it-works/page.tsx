import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ArrowRight, FileUp, Sparkles, AlertTriangle, MessageSquare } from "lucide-react";

export const metadata: Metadata = {
  title: "How It Works - Mbiu",
  description: "Learn how Mbiu breaks down complex music contracts in plain language.",
};

const steps = [
  {
    icon: FileUp,
    num: "01",
    title: "Upload your contract",
    desc: "Upload your text PDF from your phone or laptop. We process it in memory. We never store your contract on our servers.",
  },
  {
    icon: Sparkles,
    num: "02",
    title: "Automatic clause splitting",
    desc: "Mbiu separates your agreement into individual clauses in seconds. Standard boilerplate clauses are neatly organized.",
  },
  {
    icon: AlertTriangle,
    num: "03",
    title: "Risk & impact detection",
    desc: "We compare terms against reviewed Kenyan and international music contracts. High-impact clauses on royalties and rights are flagged first.",
  },
  {
    icon: MessageSquare,
    num: "04",
    title: "Questions to ask",
    desc: "For every flagged clause, Mbiu gives you plain-language explanations. You get direct questions to ask before signing.",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[900px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
            Process Overview
          </span>

          <h1 className="mt-4 font-serif text-[2.2rem] font-semibold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            How Mbiu Works
          </h1>

          <p className="mt-3 text-[1rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            Clear contract analysis in four simple steps.
          </p>

          <div className="mt-10 grid gap-6 sm:grid-cols-2">
            {steps.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.num}
                  className="rounded-2xl border border-mbiu-ink/10 bg-white/50 p-6 backdrop-blur-sm dark:border-white/10 dark:bg-white/[0.04]"
                >
                  <div className="flex items-center justify-between">
                    <div className="grid h-10 w-10 place-items-center rounded-xl bg-mbiu-indigo/10 text-mbiu-indigo dark:bg-white/10 dark:text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="font-serif text-[1.1rem] font-bold text-mbiu-ink/40 dark:text-white/40">
                      {s.num}
                    </span>
                  </div>

                  <h2 className="mt-4 font-serif text-[1.2rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                    {s.title}
                  </h2>
                  <p className="mt-2 text-[0.92rem] leading-relaxed text-mbiu-ink/80 dark:text-[#B9C1C5]">
                    {s.desc}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-10 flex flex-wrap items-center gap-4 border-t border-mbiu-ink/10 pt-8 dark:border-white/10">
            <Link
              href="/#upload"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-6 py-3 text-[0.95rem] font-semibold text-white shadow-md transition hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
            >
              Upload your contract
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/results"
              className="inline-flex items-center justify-center rounded-full border border-mbiu-ink/20 px-6 py-3 text-[0.95rem] font-semibold text-mbiu-ink transition hover:bg-black/5 dark:border-white/20 dark:text-[#F6F2E9] dark:hover:bg-white/5"
            >
              View sample analysis
            </Link>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
