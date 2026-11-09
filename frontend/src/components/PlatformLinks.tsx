import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export interface PlatformLinksProps {
  className?: string;
}

export function PlatformLinks({ className = "" }: PlatformLinksProps) {
  return (
    <div className={`flex flex-col gap-3 ${className}`}>
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
  );
}
