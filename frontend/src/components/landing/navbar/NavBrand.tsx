import React from "react";
import Image from "next/image";

export interface NavBrandProps {
  href: string;
  onClick?: () => void;
  className?: string;
}

export function NavBrand({ href, onClick, className = "" }: NavBrandProps) {
  return (
    <a
      href={href}
      className={`flex shrink-0 items-center gap-1 sm:gap-1.5 pl-0.5 transition hover:opacity-90 ${className}`}
      aria-label="Mbiu home"
      onClick={onClick}
    >
      <Image
        src="/brand/mbiu-horn.png"
        alt=""
        width={972}
        height={590}
        priority
        className="h-9 w-auto sm:h-10.5 dark:invert object-contain"
      />
      <span className="text-[1.2rem] font-extrabold tracking-[-0.06em] leading-none text-mbiu-ink sm:text-[1.4rem] dark:text-[#F6F2E9]">
        mbiu
      </span>
    </a>
  );
}
