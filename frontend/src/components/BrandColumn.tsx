import React from "react";
import Image from "next/image";
import Link from "next/link";

export interface BrandColumnProps {
  className?: string;
}

export function BrandColumn({ className = "" }: BrandColumnProps) {
  return (
    <div className={`flex flex-col gap-4 lg:col-span-5 ${className}`}>
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
  );
}
