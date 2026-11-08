import React from "react";
import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import {
  Scale,
  FileCheck,
  ShieldAlert,
  Globe,
  UserCheck,
  Cpu,
  Lock,
  Ban,
  Briefcase,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service - Mbiu",
  description:
    "Terms and guidelines governing your use of the Mbiu contract evaluation platform.",
};

export default function TermsPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[1280px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="w-full max-w-[880px] text-left">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <Scale className="h-3.5 w-3.5" />
              Terms of Service
            </span>
          </div>

          <h1 className="mt-4 font-sans text-[2.2rem] font-extrabold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Terms of Service
          </h1>

          <p className="mt-3 text-[1.05rem] leading-relaxed text-mbiu-ink/80 dark:text-[#c2c9cd]">
            Clear, binding rules governing your use of the Mbiu platform.
          </p>

          <div className="mt-10 space-y-9 text-[0.98rem] leading-relaxed text-mbiu-ink/85 dark:text-[#d2d9de]">
            {/* Section 1 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Briefcase className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
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
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <UserCheck className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
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
                legal duty owed to a record label, publisher, or partner.
              </p>
            </section>

            {/* Section 3 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Cpu className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                3. Not Legal Advice &amp; AI Disclaimer
              </h2>
              <p className="mt-2.5">
                <strong>Educational purpose only:</strong> Mbiu is an automated contract literacy tool
                powered by Large Language Models (including Google Gemini API). It is designed to
                democratize understanding of standard terms in the Kenyan creative economy.
              </p>
              <p className="mt-2">
                <strong>No advocate-client relationship:</strong> Mbiu is not a law firm. Using Mbiu
                does not create an advocate-client, legal, fiduciary, or professional relationship.
              </p>
              <p className="mt-2">
                <strong>Possibility of errors:</strong> Automated explanations may contain
                inaccuracies, omissions, or hallucinations. Mbiu does not determine legal
                enforceability under Kenyan courts. Always consult a qualified entertainment or
                intellectual property advocate licensed in Kenya before executing any binding agreement.
              </p>
            </section>

            {/* Section 4 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <FileCheck className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                4. 100% Artist Intellectual Property Ownership
              </h2>
              <p className="mt-2.5">
                You retain full and exclusive ownership of your musical works, sound recordings,
                master rights, lyrics, and uploaded contract text under the Kenya Copyright Act (Cap
                130).
              </p>
              <p className="mt-2">
                Submitting a document to Mbiu never transfers, licenses, or assigns any intellectual
                property or commercial rights to Mbiu or KamiLimu.
              </p>
            </section>

            {/* Section 5 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Lock className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
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
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Ban className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                6. Acceptable Use
              </h2>
              <p className="mt-2.5">
                You agree to use Mbiu solely for personal or authorized educational contract review.
                You agree not to:
              </p>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[0.94rem]">
                <li>Upload malicious software, corrupted files, or non-contract materials.</li>
                <li>Scrape, automate, or reverse-engineer Mbiu&apos;s prompts, scoring, or APIs.</li>
                <li>Bypass security checks, rate limits, or Cloudflare Turnstile verification.</li>
                <li>Use Mbiu to generate deceptive legal claims or harass counterparties.</li>
              </ul>
            </section>

            {/* Section 7 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <ShieldAlert className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                7. Limitation of Liability (&ldquo;As-Is&rdquo;)
              </h2>
              <p className="mt-2.5">
                Mbiu is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis
                without warranty of any kind, whether express or implied.
              </p>
              <p className="mt-2">
                Neither the Mbiu team nor KamiLimu Limited shall be liable for any direct, indirect,
                incidental, or consequential damages, commercial disputes, financial losses, or
                unfavourable terms entered into by users following automated analysis.
              </p>
            </section>

            {/* Section 8 */}
            <section className="border-t border-mbiu-ink/15 pt-7 dark:border-white/15">
              <h2 className="flex items-center gap-2.5 font-sans text-[1.3rem] font-bold text-mbiu-ink dark:text-[#F6F2E9]">
                <Globe className="h-5 w-5 text-mbiu-indigo dark:text-mbiu-indigo-dark" />
                8. Governing Law &amp; Jurisdiction
              </h2>
              <p className="mt-2.5">
                These Terms are governed by the Laws of the Republic of Kenya, including the Law of
                Contract Act (Cap 23) and the Copyright Act (Cap 130).
              </p>
              <p className="mt-2">
                Any legal proceeding arising out of or related to these Terms shall be instituted
                exclusively in the competent courts of Nairobi, Kenya.
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
