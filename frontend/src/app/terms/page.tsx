import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Scale, AlertCircle, FileCheck, ShieldAlert, Globe } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service - Mbiu",
  description: "Terms and guidelines for using the Mbiu contract evaluation platform.",
};

export default function TermsPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[840px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <Scale className="h-3.5 w-3.5" />
              Terms &amp; Guidelines
            </span>
          </div>

          <h1 className="mt-4 font-serif text-[2.2rem] font-semibold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Terms of Service
          </h1>

          <p className="mt-3 text-[1rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            Informational guidelines governing your use of Mbiu.
          </p>

          <div className="mt-8 space-y-8 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <AlertCircle className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                1. Not Legal Advice
              </h2>
              <p className="mt-2.5">
                Mbiu is an educational platform. We provide automated clause comparisons. We are not
                a law firm. We do not provide formal legal counsel. Always consult a qualified lawyer
                for binding agreements.
              </p>
            </section>

            {/* Section 2 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <FileCheck className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                2. Artist Ownership
              </h2>
              <p className="mt-2.5">
                You retain full copyright over your music and uploaded files. You confirm you have
                the right to review the uploaded agreement.
              </p>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <ShieldAlert className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                3. Independent Platform
              </h2>
              <p className="mt-2.5">
                Mbiu is an independent civic project. We are not affiliated with any record label,
                music publisher, or collective management organisation.
              </p>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="flex items-center gap-2.5 font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                <Globe className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                4. Governing Law
              </h2>
              <p className="mt-2.5">
                These terms are governed by the Laws of the Republic of Kenya.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
