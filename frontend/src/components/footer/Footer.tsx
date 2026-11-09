import React from "react";
import { BrandColumn } from "./BrandColumn";
import { LegalLinks } from "./LegalLinks";
import { PlatformLinks } from "./PlatformLinks";

export interface FooterProps {
  basePath?: string;
  className?: string;
}

export function Footer({ className = "" }: FooterProps) {
  return (
    <footer
      className={`app-footer relative z-10 w-full border-t border-[#e2d5c3] bg-transparent text-mbiu-ink transition-colors dark:border-white/10 dark:text-[#E7E0D4] ${className}`}
    >
      <div className="mx-auto max-w-[1280px] px-4 pt-12 pb-5 sm:px-8 sm:pt-16 sm:pb-6">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-12">
          <BrandColumn />
          <div className="flex justify-between gap-10 sm:justify-end sm:gap-16 lg:col-span-7 lg:ml-auto lg:gap-24">
            <PlatformLinks />
            <LegalLinks />
          </div>
        </div>

        <div className="mt-8 flex items-center justify-center border-t border-[#e2d5c3] pt-4 text-[0.84rem] text-mbiu-ink/60 dark:border-white/10 dark:text-[#88949b] sm:mt-10 sm:pt-4">
          <p className="text-center">© 2026 Mbiu. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
