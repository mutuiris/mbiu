import React from "react";
import { ArrowRight } from "lucide-react";

export interface NavCtaProps {
  href: string;
  onClick?: () => void;
  className?: string;
}

export function NavCta({ href, onClick, className = "" }: NavCtaProps) {
  return (
    <div
      className={`hidden md:block rounded-full bg-mbiu-ink/[0.04] p-1 dark:bg-white/[0.05] ${className}`}
    >
      <a
        href={href}
        onClick={onClick}
        className="inline-flex h-10 lg:h-11 items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-4 lg:px-6 text-[0.9rem] font-semibold text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea] dark:focus-visible:outline-mbiu-indigo-dark"
      >
        <span>Upload your contract</span>
        <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
      </a>
    </div>
  );
}
