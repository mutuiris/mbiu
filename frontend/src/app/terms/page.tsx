import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Terms of Service — Mbiu",
  description:
    "Guidelines and informational terms governing the use of the Mbiu contract evaluation platform.",
};

export default function TermsPage() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink transition-colors dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="flex-1 px-4 py-8 sm:px-8 sm:py-12">
        <div className="mx-auto w-full max-w-[1280px]">
          {/* Page Header */}
          <div className="mb-10 text-left">
            <h1 className="font-serif text-[2.2rem] font-bold tracking-tight text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
              Terms of Service
            </h1>
            <p className="mt-2 max-w-[760px] text-[1.02rem] leading-relaxed text-mbiu-ink/75 dark:text-[#B9C1C5]">
              Guidelines and informational terms governing the use of the Mbiu contract evaluation
              platform.
            </p>
          </div>

          {/* Content Column - Max Width 840px, Left-aligned */}
          <div className="mb-16 max-w-[840px] text-left">
            <div className="flex flex-col gap-8">
              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  1. About Mbiu &amp; Support
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Mbiu is a legal-tech educational initiative created by The Agwambos through the
                  Innovation Pillar competition at KamiLimu. The project has been mentored and
                  supported by KamiLimu Limited (Nairobi, Kenya) from problem and solution validation
                  through to operational funding.
                </p>
                <p className="mt-3 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
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
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  2. Eligibility, Authority &amp; Confidentiality
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  <strong>Age limit (18+):</strong> You must be at least 18 years old to use Mbiu.
                  Minors may not submit documents directly.
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  <strong>Authority to upload:</strong> You confirm and warrant that you are either a
                  named party to the uploaded contract or specifically authorized by the artist or
                  rights-holder to submit it for review.
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  <strong>Third-party NDAs:</strong> You confirm that uploading the contract does not
                  breach any third-party Non-Disclosure Agreement (NDA), confidentiality clause, or
                  legal duty owed to a record label, publisher, or commercial partner.
                </p>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  3. Informational Purpose &amp; Not Legal Advice
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Mbiu provides plain-language clause explanations, comparative analysis against
                  industry standard templates, and suggested inquiry questions for educational and
                  civic contract literacy purposes. The content provided on this platform does{" "}
                  <strong>not</strong> constitute formal legal counsel.
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  <strong>No advocate-client relationship:</strong> Using Mbiu does not create an
                  advocate-client, legal, or fiduciary relationship. Mbiu uses automated Large Language
                  Models (Google Gemini API), and outputs may occasionally contain errors or omissions.
                  Musicians should consult licensed entertainment or intellectual property advocates for
                  binding legal advice.
                </p>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  4. 100% Artist Intellectual Property Ownership
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  You retain full, exclusive copyright and moral rights over your musical works, sound
                  recordings, master tracks, lyrics, and uploaded contract text under the Kenya
                  Copyright Act (Cap 130).
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Submitting a document to Mbiu never transfers, licenses, or assigns any intellectual
                  property or commercial rights to Mbiu or KamiLimu.
                </p>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  5. Zero-Storage Architecture
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Mbiu operates on a strict zero-storage architecture. Your contract is evaluated purely
                  in volatile computer memory (RAM).
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  We never write contract files to databases, permanent disks, or application logs. Once
                  the analysis stream finishes or you close your browser tab, the contract data is
                  completely purged.
                </p>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  6. Acceptable Use
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  You agree to use Mbiu solely for lawful, authorized contract review. You agree not to:
                </p>
                <ul className="mt-2 flex flex-col gap-2 pl-6 list-disc text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  <li>Upload malicious software, corrupted files, or non-contract materials.</li>
                  <li>Scrape, automate, or reverse-engineer Mbiu&apos;s prompts, scoring, or APIs.</li>
                  <li>Bypass security checks, rate limits, or Cloudflare Turnstile verification.</li>
                  <li>Use Mbiu to generate deceptive claims or harass counterparties.</li>
                </ul>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  7. Limitations of Liability (&ldquo;As-Is&rdquo;)
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Mbiu is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis
                  without warranty of any kind, whether express or implied.
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Neither the Mbiu team nor KamiLimu Limited shall be liable for any direct, indirect,
                  incidental, or consequential damages, commercial disputes, financial losses, or
                  unfavourable contract terms entered into following automated analysis.
                </p>
              </div>

              <div>
                <h2 className="mb-2.5 font-serif text-[1.35rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                  8. Governing Law &amp; Jurisdiction
                </h2>
                <p className="text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  These Terms are governed by and construed in accordance with the Laws of the
                  Republic of Kenya, including the Law of Contract Act (Cap 23) and the Copyright Act
                  (Cap 130).
                </p>
                <p className="mt-2 text-[1rem] leading-[1.75] text-mbiu-ink/80 dark:text-[#d2d9de]">
                  Any legal proceeding arising out of or related to these Terms shall be instituted
                  exclusively in the competent courts of Nairobi, Kenya.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-[#e2d5c3] bg-transparent py-8 text-[0.875rem] text-mbiu-ink/70 transition-colors dark:border-white/10 dark:text-[#88949b]">
        <div className="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-3 px-4 sm:flex-row sm:px-8">
          <div>© 2026 Mbiu. All rights reserved.</div>
          <div className="flex items-center gap-3 text-[0.84rem]">
            <span>Kenya Creative Economy Civic Project</span>
            <span>·</span>
            <span>Supported by KamiLimu</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
