import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy — Mbiu",
  description:
    "How Mbiu collects, uses, and safeguards your data under the Kenya Data Protection Act (KDPA) 2019.",
};

export default function PrivacyPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink transition-colors dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-8 sm:py-10">
        {/* Back Arrow at Top */}
        <div className="mb-6">
          <Link
            href="/"
            className="group inline-flex items-center gap-2 text-[0.92rem] font-medium text-mbiu-ink/75 transition-colors hover:text-mbiu-indigo dark:text-[#B9C1C5] dark:hover:text-white"
            aria-label="Back to home"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            <span>Back to Home</span>
          </Link>
        </div>

        {/* Full-width Card Body spanning from left edge to right edge */}
        <div className="w-full rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10 md:p-12">
          <h1 className="font-serif text-[1.5rem] font-semibold tracking-[-0.025em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.85rem]">
            Privacy Policy
          </h1>

          <p className="mt-2 text-[0.95rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            How Mbiu protects your contracts under the Kenya Data Protection Act (KDPA) 2019.
          </p>

          <div className="mt-7 space-y-7 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/10 pt-5 dark:border-white/10">
              <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
                1. Data Controller &amp; Governance
              </h2>
              <p className="mt-2">
                Mbiu was created by The Agwambos through the{" "}
                <a
                  href="https://www.kamilimu.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  KamiLimu
                </a>{" "}
                Innovation Pillar competition and is supported by{" "}
                <a
                  href="https://www.kamilimu.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  KamiLimu Limited
                </a>{" "}
                (Nairobi, Kenya). The legal data controller is the Mbiu team, with data protection
                governance managed through{" "}
                <a
                  href="https://www.kamilimu.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  KamiLimu
                </a>
                . We strictly adhere to the principles set out in the{" "}
                <strong>Kenya Data Protection Act, 2019 (KDPA)</strong> and the guidelines of the
                Office of the Data Protection Commissioner (ODPC).
              </p>
              <p className="mt-2">
                <strong>Registered Address:</strong> Nairobi, Kenya.
              </p>
              <p className="mt-2 text-[0.88rem] text-mbiu-ink/60 dark:text-[#9aa5aa]">
                <em>Regulatory notice:</em> As an early-stage civic initiative engineered around a strict
                zero-storage model, Mbiu is not yet formally registered with the ODPC.
              </p>
            </section>

            {/* Section 2 */}
            <section className="border-t border-mbiu-ink/10 pt-5 dark:border-white/10">
              <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
                2. We Do Not Collect Personal Data
              </h2>
              <p className="mt-2">
                Mbiu is deliberately built to operate without collecting user personal identities:
              </p>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[0.92rem]">
                <li>
                  <strong>No account creation:</strong> You do not need to register, log in, or provide
                  your name, phone number, or email address.
                </li>
                <li>
                  <strong>No payment details:</strong> Mbiu is currently free; no billing or credit card
                  data is requested or stored.
                </li>
                <li>
                  <strong>No tracking cookies:</strong> We do not track you across the web or deploy
                  advertising pixels.
                </li>
              </ul>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/10 pt-5 dark:border-white/10">
              <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
                3. Zero-Storage Evaluation
              </h2>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[0.92rem]">
                <li>
                  We <strong>never</strong> save your contract.
                </li>
                <li>
                  We never sell your data, share your agreements with record labels, or train
                  artificial intelligence models on your creative works.
                </li>
              </ul>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/10 pt-5 dark:border-white/10">
              <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
                4. Artist Rights &amp; Past Document Retrieval
              </h2>
              <p className="mt-2">
                Under the Kenya Data Protection Act 2019 (Sections 26–40), data subjects possess rights
                of access, rectification, and erasure.
              </p>
              <p className="mt-3 rounded-xl border border-mbiu-ink/10 bg-mbiu-peach/30 p-4 text-[0.95rem] leading-[1.7] text-mbiu-ink dark:border-white/10 dark:bg-white/[0.04] dark:text-[#F6F2E9]">
                <strong>Important notice regarding past contracts:</strong> Because Mbiu operates on a
                strict zero-storage model and never stores your agreements, Mbiu cannot retrieve,
                provide copies of, or delete past contracts because none are ever saved in any database.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
