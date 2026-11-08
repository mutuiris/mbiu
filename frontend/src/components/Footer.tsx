import React from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export interface FooterProps {
  basePath?: string;
  className?: string;
}

export function Footer({ className = "" }: FooterProps) {
  return (
    <footer
      className={`app-footer relative z-10 w-full border-t border-[#e2d5c3] bg-transparent text-mbiu-ink transition-colors dark:border-white/10 dark:text-[#E7E0D4] ${className}`}
    >
      <div className="mx-auto max-w-[1280px] px-4 py-12 sm:px-8 sm:py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-12">
          {/* Brand & Overview Column */}
          <div className="flex flex-col gap-4 lg:col-span-5">
            <Link
              href="/"
              className="flex items-center gap-1 sm:gap-1.5 transition hover:opacity-90"
              aria-label="Mbiu home"
            >
              <Image
                src="/brand/mbiu-horn.png"
                alt=""
                width={972}
                height={590}
                className="h-8 w-auto dark:invert object-contain sm:h-9"
              />
              <span className="text-[1.25rem] font-extrabold tracking-[-0.06em] leading-none text-mbiu-ink sm:text-[1.4rem] dark:text-[#F6F2E9]">
                mbiu
              </span>
            </Link>

            <p className="text-[0.9rem] leading-relaxed text-mbiu-ink/80 dark:text-[#B9C1C5]">
              A tool that helps Kenyan musicians understand a music contract before they sign:
              clause-by-clause comparison with reviewed standard templates, in plain language. Not
              legal advice.
            </p>

            <p className="text-[0.84rem] leading-relaxed text-mbiu-ink/70 dark:text-[#9aa5aa]">
              Supported by{" "}
              <a
                href="https://www.kamilimu.org/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo hover:decoration-mbiu-indigo dark:text-[#F6F2E9] dark:decoration-white/30 dark:hover:text-white"
              >
                KamiLimu
              </a>
              .
            </p>
          </div>

          {/* Navigation Link Columns */}
          <div className="flex justify-between gap-10 sm:justify-end sm:gap-16 lg:col-span-7 lg:ml-auto lg:gap-24">
            {/* Platform Column */}
            <div className="flex flex-col gap-3">
              <h4 className="font-serif text-[1rem] font-bold tracking-tight text-mbiu-ink dark:text-[#F6F2E9]">
                Platform
              </h4>
              <ul className="flex flex-col gap-2.5 text-[0.9rem] text-mbiu-ink/80 dark:text-[#B9C1C5]">
                <li>
                  <Link
                    href="/"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Home
                  </Link>
                </li>
                <li>
                  <Link
                    href="/#how-it-works"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    How It Works
                  </Link>
                </li>
                <li>
                  <Link
                    href="/#about"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    About
                  </Link>
                </li>
                <li>
                  <Link
                    href="/#upload"
                    className="group inline-flex items-center gap-1.5 transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    <span>Upload Contract</span>
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </li>
                <li>
                  <Link
                    href="/team"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Our Team
                  </Link>
                </li>
              </ul>
            </div>

            {/* Privacy & Legal Column */}
            <div className="flex flex-col gap-3">
              <h4 className="font-serif text-[1rem] font-bold tracking-tight text-mbiu-ink dark:text-[#F6F2E9]">
                Privacy &amp; Legal
              </h4>
              <ul className="flex flex-col gap-2.5 text-[0.9rem] text-mbiu-ink/80 dark:text-[#B9C1C5]">
                <li>
                  <Link
                    href="/privacy"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link
                    href="/terms"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 flex items-center justify-center border-t border-[#e2d5c3] pt-6 text-[0.84rem] text-mbiu-ink/60 dark:border-white/10 dark:text-[#88949b]">
          <p className="text-center">© 2026 Mbiu. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
