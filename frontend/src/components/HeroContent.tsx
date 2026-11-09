import React from "react";
import { ArrowRight, Lock } from "lucide-react";

export interface HeroContentProps {
  uploadHref?: string;
  className?: string;
}

const primaryButton =
  "inline-flex items-center justify-center gap-2.5 rounded-full bg-mbiu-indigo text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea] dark:focus-visible:outline-mbiu-indigo-dark";

export function HeroContent({
  uploadHref = "#upload",
  className = "",
}: HeroContentProps) {
  return (
    <div
      className={`mx-auto flex w-full max-w-[720px] flex-col items-center text-center xl:mx-0 xl:items-start xl:text-left ${className}`}
    >
      <h1 className="font-serif text-[clamp(2.15rem,5.5vw,4.5rem)] font-medium leading-[1.04] tracking-[-0.035em] text-mbiu-ink dark:text-[#F6F2E9] xl:leading-[0.92]">
        Understand your contract before you sign it.
      </h1>

      <p className="mt-5 text-[1.1rem] font-bold tracking-[-0.01em] text-mbiu-ink dark:text-[#F6F2E9] sm:mt-6 sm:text-[1.28rem]">
        Your music. Your rights. Your decisions.
      </p>
      <p className="mt-3 max-w-[480px] text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#B9C1C5] sm:mt-4 sm:text-[1.02rem] sm:leading-7">
        Upload your music contract and understand what you&apos;re agreeing to, what could
        affect you, and what questions to ask before signing.
      </p>

      <div className="mt-7 sm:mt-8 flex w-full justify-center xl:justify-start">
        <a
          href={uploadHref}
          className={`${primaryButton} h-[50px] w-full max-w-[320px] px-7 text-[0.98rem] sm:h-[52px] sm:w-auto sm:max-w-none sm:px-8 sm:text-[1.02rem]`}
        >
          Upload your contract
          <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2.2} />
        </a>
      </div>

      <p className="mt-4 flex items-center justify-center gap-2 text-[0.82rem] font-medium text-mbiu-ink/70 dark:text-[#B9C1C5] sm:mt-5 sm:text-[0.85rem] xl:justify-start">
        <Lock className="h-4 w-4 shrink-0" strokeWidth={2} />
        Mbiu does not store your contracts on our servers.
      </p>
    </div>
  );
}
