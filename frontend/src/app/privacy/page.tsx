import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import {
  ShieldCheck,
  Lock,
  EyeOff,
  CheckCircle2,
  ServerOff,
  ArrowRightLeft,
  FileQuestion,
  Building2,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy - Mbiu",
  description:
    "How Mbiu protects your music agreements and handles data under the Kenya Data Protection Act 2019.",
};

export default function PrivacyPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[1280px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="w-full max-w-[880px] text-left">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <Lock className="h-3.5 w-3.5" />
              Privacy &amp; Data Protection
            </span>
          </div>

          <h1 className="mt-4 font-sans text-[2.2rem] font-extrabold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Privacy Policy
          </h1>

          <p className="mt-3 text-[1.05rem] leading-relaxed text-mbiu-ink/80 dark:text-[#c2c9cd]">
            How Mbiu protects your contracts under the Kenya Data Protection Act (KDPA) 2019.
          </p>

          <div className="mt-10 space-y-9 text-[0.98rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Building2 className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                1. Data Controller &amp; Governance
              </h2>
              <p className="mt-2.5">
                Mbiu was created by The Agwambos through the KamiLimu Innovation Pillar competition
                and is supported by KamiLimu Limited (Nairobi, Kenya). The legal data controller is
                the Mbiu team, with data protection governance managed through KamiLimu.
              </p>
              <p className="mt-2">
                <strong>Registered Address:</strong> Nairobi, Kenya.
              </p>
              <p className="mt-2">
                <strong>Data Protection Inquiries:</strong> Contact KamiLimu at{" "}
                <a
                  href="mailto:info@kamilimu.org"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  info@kamilimu.org
                </a>
                .
              </p>
              <p className="mt-2 text-[0.88rem] text-mbiu-ink/75 dark:text-[#a0aab0]">
                <em>Regulatory status:</em> As an early-stage civic initiative engineered around a
                strict zero-storage model, Mbiu is not yet formally registered with the Office of the
                Data Protection Commissioner (ODPC) Kenya.
              </p>
            </section>

            {/* Section 2 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <ServerOff className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                2. We Do Not Collect Personal Data
              </h2>
              <p className="mt-2.5">
                Mbiu is deliberately built to operate without collecting user personal identities:
              </p>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[0.94rem]">
                <li>
                  <strong>No account creation:</strong> You do not need to register, log in, or
                  provide your name, phone number, or email address.
                </li>
                <li>
                  <strong>No payment details:</strong> Mbiu is currently free; no billing or credit
                  card data is requested or stored.
                </li>
                <li>
                  <strong>No advertising cookies:</strong> We do not track you across websites or
                  deploy advertising pixels.
                </li>
                <li>
                  <strong>Anonymous telemetry only:</strong> Error monitoring (Sentry) and server
                  logs record only aggregate operational metrics (durations, error categories). They
                  never capture contract text or artist names.
                </li>
              </ul>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <EyeOff className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                3. Zero-Storage Evaluation
              </h2>
              <p className="mt-2.5">
                Your uploaded PDF contract is processed entirely in temporary volatile memory (RAM).
              </p>
              <p className="mt-2">
                We <strong>never</strong> save your contract to a database, hard drive, or
                application log. We never sell your data, share your agreements with record labels, or
                train artificial intelligence models on your creative works.
              </p>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <CheckCircle2 className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                4. Instant Memory Purge &amp; Browser Storage
              </h2>
              <p className="mt-2.5">
                <strong>Server-side:</strong> As soon as the analysis stream completes, server memory
                allocated to your contract is released immediately.
              </p>
              <p className="mt-2">
                <strong>Client-side:</strong> Results live in your browser tab. If you enable the
                optional &ldquo;Keep results&rdquo; toggle, results are cached in your device&apos;s
                temporary browser session for up to 60 minutes to prevent loss on page refresh.
                Closing the tab or clicking &ldquo;Check another contract&rdquo; purges them
                immediately.
              </p>
            </section>

            {/* Section 5 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <ArrowRightLeft className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                5. Cross-Border Data Transfers (KDPA Sections 48 &amp; 49)
              </h2>
              <p className="mt-2.5">
                To evaluate clauses, Mbiu uses secure third-party processing. Under Kenya&apos;s Data
                Protection Act 2019, these are treated as cross-border data transfers:
              </p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-[0.94rem]">
                <li>
                  <strong>Google Gemini API (Paid Tier):</strong> Receives clause text, linked
                  clauses, and template excerpts for comparison. Storage is disabled (
                  <code>store=False</code>), and Google does not use prompts to train AI models.
                </li>
                <li>
                  <strong>OpenAI API (Failover Only):</strong> An emergency backup called only if
                  Gemini is unavailable, with persistent storage disabled on every call (
                  <code>store: false</code>).
                </li>
                <li>
                  <strong>Cloudflare Turnstile:</strong> Receives a single-use verification token to
                  prevent bot abuse. Never touches contract text.
                </li>
                <li>
                  <strong>Supabase:</strong> Hosts standard public reference templates only. Holds
                  zero user contracts.
                </li>
              </ul>
            </section>

            {/* Section 6 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <FileQuestion className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                6. Artist Rights &amp; Past Document Retrieval
              </h2>
              <p className="mt-2.5">
                Under the Kenya Data Protection Act 2019 (Sections 26–40), data subjects possess
                rights of access, rectification, and erasure.
              </p>
              <p className="mt-2 font-medium text-mbiu-ink dark:text-[#F6F2E9]">
                Important notice regarding past contracts: Because Mbiu operates on a strict
                zero-storage model and never stores your agreements, Mbiu cannot retrieve, provide
                copies of, or delete past contracts because none are ever saved.
              </p>
            </section>

            {/* Section 7 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <ShieldCheck className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                7. Contact
              </h2>
              <p className="mt-2.5">
                For questions regarding this Privacy Policy, contact KamiLimu at{" "}
                <a
                  href="mailto:info@kamilimu.org"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  info@kamilimu.org
                </a>
                , Nairobi, Kenya.
              </p>
            </section>
          </div>
        </div>
      </main>

      <footer className="mx-auto mt-20 w-full max-w-[1280px] border-t border-mbiu-ink/15 px-4 py-8 text-[0.84rem] text-mbiu-ink/60 dark:border-white/10 dark:text-[#88949b] sm:px-8">
        <p>© 2026 Mbiu. All rights reserved.</p>
      </footer>
    </div>
  );
}
