import React from "react";
import Image from "next/image";
import Link from "next/link";

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
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-mbiu-ink text-white dark:bg-[#1a2c35] dark:text-[#F6F2E9]">
                <Image
                  src="/brand/mbiu-horn.png"
                  alt=""
                  width={24}
                  height={24}
                  className="h-5 w-auto object-contain invert dark:invert-0"
                />
              </div>
              <span className="font-serif text-[1.35rem] font-bold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9]">
                Mbiu
              </span>
            </div>

            <p className="text-[0.9rem] leading-relaxed text-mbiu-ink/80 dark:text-[#B9C1C5]">
              Democratizing contract clarity and creative rights for Kenya&apos;s independent music
              artists.
            </p>

            <p className="text-[0.84rem] leading-relaxed text-mbiu-ink/75 dark:text-[#9aa5aa]">
              This project was part of the 2026{" "}
              <a
                href="https://www.mozillafoundation.org/en/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo hover:decoration-mbiu-indigo dark:text-[#F6F2E9] dark:decoration-white/30 dark:hover:text-white"
              >
                Mozilla
              </a>{" "}
              x{" "}
              <a
                href="https://www.kamilimu.org/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo hover:decoration-mbiu-indigo dark:text-[#F6F2E9] dark:decoration-white/30 dark:hover:text-white"
              >
                KamiLimu
              </a>{" "}
              Buildathon and has been funded by{" "}
              <a
                href="https://www.mozillafoundation.org/en/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo hover:decoration-mbiu-indigo dark:text-[#F6F2E9] dark:decoration-white/30 dark:hover:text-white"
              >
                Mozilla Foundation
              </a>
              .
            </p>

            <p className="text-[0.81rem] leading-relaxed text-mbiu-ink/65 dark:text-[#88949b]">
              <strong className="font-semibold text-mbiu-ink/90 dark:text-[#d3dbe0]">
                Independent Civic Resource:
              </strong>{" "}
              Mbiu is an independent educational contract review tool. It is not affiliated with or
              operating on behalf of any record label or management firm. It does not provide legal
              advice. Always consult a qualified lawyer for binding agreements.
            </p>
          </div>

          {/* Navigation Link Columns */}
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:col-span-7">
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
                    href="/#upload"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Upload Contract
                  </Link>
                </li>
              </ul>
            </div>

            {/* About Column */}
            <div className="flex flex-col gap-3">
              <h4 className="font-serif text-[1rem] font-bold tracking-tight text-mbiu-ink dark:text-[#F6F2E9]">
                About
              </h4>
              <ul className="flex flex-col gap-2.5 text-[0.9rem] text-mbiu-ink/80 dark:text-[#B9C1C5]">
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
                    href="/team"
                    className="transition-colors hover:text-mbiu-indigo dark:hover:text-white"
                  >
                    Our Team
                  </Link>
                </li>
              </ul>
            </div>

            {/* Privacy & Legal Column */}
            <div className="col-span-2 flex flex-col gap-3 sm:col-span-1">
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
        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-[#e2d5c3] pt-6 text-[0.84rem] text-mbiu-ink/60 dark:border-white/10 dark:text-[#88949b] sm:flex-row">
          <div>© 2026 Mbiu. All rights reserved.</div>
          <div className="flex items-center gap-2">
            <span>Kenya Music Contract Project</span>
            <span>·</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
