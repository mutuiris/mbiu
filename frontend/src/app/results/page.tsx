"use client";

import { ArrowRight, Lock } from "lucide-react";
import React, { useState } from "react";

import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";
import { LiveResults } from "@/components/results/LiveResults";
import { SiteBackdrop } from "@/components/SiteBackdrop";
import { createSyntheticEventStream } from "@/lib/api/syntheticStream";
import type { EvaluationEvent } from "@/lib/api/stream";

export default function ResultsPage() {
  const [stream, setStream] = useState<AsyncGenerator<EvaluationEvent, void, unknown> | null>(null);

  const startSyntheticDemo = () => setStream(createSyntheticEventStream(350));

  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <SiteBackdrop variant="results" />

      <Navbar basePath="/" />

      <main className="results-page relative z-10 mx-auto w-full max-w-[880px] px-5 pb-20 pt-10 sm:px-8 sm:pt-14">
        <header className="max-w-[620px]">
          <p className="text-[0.72rem] font-bold uppercase tracking-[0.22em] text-mbiu-indigo dark:text-[#a9b0ff]">
            Contract check
          </p>
          <h1
            className={`mt-3 font-serif font-medium leading-[1.05] tracking-[-0.03em] text-mbiu-ink transition-all dark:text-[#F6F2E9] ${
              stream
                ? "text-[1.45rem] sm:text-[1.75rem]"
                : "text-[clamp(1.6rem,2.8vw,2.25rem)]"
            }`}
          >
            Your contract, clause by clause.
          </h1>
          <p className="mt-3 text-[0.95rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            Real-time clause analysis. Cards appear in order of importance to you as they finish
            checking.
          </p>
        </header>

        {!stream ? (
          <section className="mt-8" aria-label="Start evaluation options">
            <div className="rounded-[28px] border border-white/70 bg-white/55 p-7 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.65)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-9">
              <span className="inline-flex items-center gap-2 rounded-full bg-mbiu-peach/40 px-3.5 py-1.5 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
                Live preview
              </span>
              <h2 className="mt-4 font-serif text-[1.25rem] font-medium leading-tight tracking-[-0.02em] dark:text-[#F6F2E9] sm:text-[1.45rem]">
                See how a contract check works.
              </h2>
              <p className="mt-3 max-w-[560px] text-[0.98rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
                Experience the live NDJSON streaming pipeline immediately with pre-recorded Kenyan
                music agreement clauses.
              </p>

              <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-3">
                <button
                  type="button"
                  onClick={startSyntheticDemo}
                  className="inline-flex h-12 items-center justify-center gap-2.5 rounded-full bg-mbiu-indigo px-6 text-[0.95rem] font-semibold text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea]"
                >
                  Start the live preview
                  <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
                </button>
                <span className="inline-flex items-center gap-1.5 text-[0.8rem] text-mbiu-ink/60 dark:text-[#98a3a9]">
                  <Lock className="h-3.5 w-3.5" strokeWidth={1.9} />
                  No upload needed for this sample.
                </span>
              </div>
            </div>
          </section>
        ) : (
          <div className="stream-viewport mt-8">
            <div className="stream-controls">
              <button
                type="button"
                className="secondary-btn restart-btn"
                onClick={startSyntheticDemo}
              >
                Restart preview
              </button>
            </div>
            <LiveResults eventStream={stream} onRetryAll={startSyntheticDemo} />
          </div>
        )}
      </main>

      <Footer basePath="/" />
    </div>
  );
}
