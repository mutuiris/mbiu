import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ShieldCheck, Lock, EyeOff, FileText, CheckCircle2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy - Mbiu",
  description: "How Mbiu protects your music agreements and handles your data.",
};

export default function PrivacyPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[840px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <Lock className="h-3.5 w-3.5" />
              Privacy &amp; Data Protection
            </span>
          </div>

          <h1 className="mt-4 font-serif text-[2.2rem] font-semibold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Privacy Policy
          </h1>

          <p className="mt-3 text-[1rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            How Mbiu protects your contracts under the Kenya Data Protection Act (KDPA) 2019.
          </p>

          <div className="mt-8 space-y-8 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <ShieldCheck className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                1. Commitment to Data Protection
              </h2>
              <p className="mt-2.5">
                Mbiu is an independent education tool. We protect your creative rights. We strictly
                follow the Kenya Data Protection Act, 2019 (KDPA). We follow all rules from the
                Office of the Data Protection Commissioner (ODPC).
              </p>
            </section>

            {/* Section 2 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <EyeOff className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                2. Zero-Storage Evaluation
              </h2>
              <p className="mt-2.5">
                Your contract is processed in temporary computer memory. We never save it to any
                database. We never write it to hard drives. We never record contract text in
                application logs.
              </p>
              <p className="mt-2">
                We never sell your data. We never share your contracts with record labels. We never
                train artificial intelligence models on your documents.
              </p>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <CheckCircle2 className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                3. Instant Memory Purge
              </h2>
              <p className="mt-2.5">
                Analysis happens in memory. Once the analysis stream finishes, memory is released. If
                you close your browser tab, your results vanish immediately.
              </p>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <FileText className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                4. Your Rights
              </h2>
              <p className="mt-2.5">
                You own 100% of your music and contracts. You retain all copyright. Using Mbiu never
                transfers any rights.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
