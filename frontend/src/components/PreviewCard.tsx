import React from "react";
import { CircleHelp, Diamond, Info, TriangleAlert } from "lucide-react";

export interface PreviewCardProps {
  className?: string;
}

export function PreviewCard({ className = "" }: PreviewCardProps) {
  return (
    <article
      className={`relative z-10 w-full max-w-[380px] rounded-[24px] border border-white/70 bg-[#fbf1e1]/70 p-5 shadow-[0_36px_90px_-32px_rgba(30,25,15,0.5)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] dark:shadow-[0_36px_90px_-34px_rgba(0,0,0,0.9)] sm:rounded-[28px] sm:p-7 xl:mt-2 ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <Diamond className="h-3.5 w-3.5 fill-[#e98a3f] text-[#e98a3f]" strokeWidth={1} />
        <span className="text-[0.88rem] font-medium text-mbiu-ink dark:text-[#EDE7DB] sm:text-[0.9rem]">
          Clause 7.2
        </span>
      </div>

      <h2 className="mt-1 text-[1.35rem] font-extrabold leading-tight tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.55rem]">
        Post-term exclusivity
      </h2>

      <span className="mt-3 inline-flex items-center gap-2 rounded-full bg-mbiu-peach px-3.5 py-1.5 text-[0.82rem] font-bold text-mbiu-warning-text sm:px-4 sm:text-[0.88rem]">
        <TriangleAlert className="h-4 w-4 shrink-0 fill-[#c2410c] text-[#c2410c]" strokeWidth={1.5} />
        Worth inquiry
      </span>

      <p className="mt-4 font-serif text-[0.98rem] italic leading-6 text-mbiu-ink/90 dark:text-[#E7DFD2]/85 sm:text-[1.02rem] sm:leading-7">
        “Your agreement could restrict you from working with other labels for two years after it
        ends.”
      </p>

      <div className="my-4 h-px w-full bg-mbiu-ink/15 dark:bg-white/15" />

      <div className="flex gap-3">
        <CircleHelp
          className="mt-0.5 h-5 w-5 shrink-0 text-mbiu-ink dark:text-[#EDE7DB]"
          strokeWidth={1.8}
        />
        <div>
          <p className="text-[0.88rem] font-bold leading-snug text-mbiu-ink dark:text-[#F6F2E9] sm:text-[0.9rem]">
            Could this affect your next opportunity?
          </p>
          <p className="mt-1.5 text-[0.85rem] leading-relaxed text-mbiu-ink/70 dark:text-[#B9C1C5] sm:text-[0.9rem]">
            “What happens if another label approaches me during this period?”
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2.5 border-t border-mbiu-ink/15 pt-4 text-[0.8rem] text-mbiu-ink/70 dark:border-white/15 dark:text-[#B9C1C5] sm:text-[0.82rem]">
        <Info className="h-[18px] w-[18px] shrink-0" strokeWidth={1.8} />
        This isn&apos;t legal advice.
      </div>
    </article>
  );
}
