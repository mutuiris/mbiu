import React from "react";
import Link from "next/link";

export interface LegalLinksProps {
  className?: string;
}

export function LegalLinks({ className = "" }: LegalLinksProps) {
  return (
    <div className={`flex flex-col gap-3 ${className}`}>
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
  );
}
