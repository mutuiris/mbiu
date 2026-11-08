import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service — Mbiu",
  description:
    "Guidelines and informational terms governing the use of the Mbiu contract evaluation platform.",
};

export default function TermsPage() {
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
          <h1 className="font-serif text-[2.2rem] font-semibold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Terms of Service
          </h1>

          <p className="mt-3 text-[1rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            Clear, binding rules governing your use of the Mbiu platform.
          </p>

          <div className="mt-8 space-y-8 text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                1. About Mbiu &amp; Support
              </h2>
              <p className="mt-2.5">
                Mbiu is a legal-tech educational initiative created by The Agwambos through the
                Innovation Pillar competition at KamiLimu. The project has been mentored and
                supported by KamiLimu Limited (Nairobi, Kenya) from problem and solution validation
                through to operational funding.
              </p>
              <p className="mt-2">
                Mbiu is currently offered as a free public educational tool. We reserve the right to
                introduce premium or paid subscription tiers in the future. Inquiries may be
                directed via KamiLimu at{" "}
                <a
                  href="mailto:info@kamilimu.org"
                  className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
                >
                  info@kamilimu.org
                </a>
                .
              </p>
            </section>

            {/* Section 2 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                2. Eligibility, Authority &amp; Confidentiality
              </h2>
              <p className="mt-2.5">
                <strong>Age limit (18+):</strong> You must be at least 18 years old to use Mbiu.
                Minors may not submit documents directly.
              </p>
              <p className="mt-2">
                <strong>Authority to upload:</strong> You confirm and warrant that you are either a
                named party to the uploaded contract or specifically authorized by the artist or
                rights-holder to submit it for review.
              </p>
              <p className="mt-2">
                <strong>Third-party NDAs:</strong> You confirm that uploading the contract does not
                breach any third-party Non-Disclosure Agreement (NDA), confidentiality clause, or
                legal duty owed to a record label, publisher, or commercial partner.
              </p>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                3. Informational Purpose &amp; Not Legal Advice
              </h2>
              <p className="mt-2.5">
                Mbiu provides plain-language clause explanations, comparative analysis against
                industry standard templates, and suggested inquiry questions for educational and
                civic contract literacy purposes. The content provided on this platform does{" "}
                <strong>not</strong> constitute formal legal counsel.
              </p>
              <p className="mt-2">
                <strong>No advocate-client relationship:</strong> Using Mbiu does not create an
                advocate-client, legal, or fiduciary relationship. Mbiu uses automated Large Language
                Models (Google Gemini API), and outputs may occasionally contain errors or omissions.
                Musicians should consult licensed entertainment or intellectual property advocates for
                binding legal advice.
              </p>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                4. 100% Artist Intellectual Property Ownership
              </h2>
              <p className="mt-2.5">
                You retain full, exclusive copyright and moral rights over your musical works, sound
                recordings, master tracks, lyrics, and uploaded contract text under the Kenya
                Copyright Act (Cap 130).
              </p>
              <p className="mt-2">
                Submitting a document to Mbiu never transfers, licenses, or assigns any intellectual
                property or commercial rights to Mbiu or KamiLimu.
              </p>
            </section>

            {/* Section 5 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                5. Zero-Storage Architecture
              </h2>
              <p className="mt-2.5">
                Mbiu operates on a strict zero-storage architecture. Your contract is evaluated purely
                in volatile computer memory (RAM).
              </p>
              <p className="mt-2">
                We never write contract files to databases, permanent disks, or application logs. Once
                the analysis stream finishes or you close your browser tab, the contract data is
                completely purged.
              </p>
            </section>

            {/* Section 6 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                6. Acceptable Use
              </h2>
              <p className="mt-2.5">
                You agree to use Mbiu solely for lawful, authorized contract review. You agree not to:
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-[0.92rem]">
                <li>Upload malicious software, corrupted files, or non-contract materials.</li>
                <li>Scrape, automate, or reverse-engineer Mbiu&apos;s prompts, scoring, or APIs.</li>
                <li>Bypass security checks, rate limits, or Cloudflare Turnstile verification.</li>
                <li>Use Mbiu to generate deceptive claims or harass counterparties.</li>
              </ul>
            </section>

            {/* Section 7 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                7. Limitations of Liability (&ldquo;As-Is&rdquo;)
              </h2>
              <p className="mt-2.5">
                Mbiu is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis
                without warranty of any kind, whether express or implied.
              </p>
              <p className="mt-2">
                Neither the Mbiu team nor KamiLimu Limited shall be liable for any direct, indirect,
                incidental, or consequential damages, commercial disputes, financial losses, or
                unfavourable contract terms entered into following automated analysis.
              </p>
            </section>

            {/* Section 8 */}
            <section className="border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
              <h2 className="font-serif text-[1.25rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                8. Governing Law &amp; Jurisdiction
              </h2>
              <p className="mt-2.5">
                These Terms are governed by and construed in accordance with the Laws of the
                Republic of Kenya, including the Law of Contract Act (Cap 23) and the Copyright Act
                (Cap 130).
              </p>
              <p className="mt-2">
                Any legal proceeding arising out of or related to these Terms shall be instituted
                exclusively in the competent courts of Nairobi, Kenya.
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
