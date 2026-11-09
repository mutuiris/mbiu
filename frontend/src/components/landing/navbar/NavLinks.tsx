import React from "react";

export interface NavLinkItem {
  label: string;
  href: string;
}

export interface NavLinksProps {
  resolveHref: (target: string) => string;
  onLinkClick?: () => void;
  className?: string;
  itemClassName?: string;
}

export const DEFAULT_NAV_LINKS: NavLinkItem[] = [
  { label: "Home", href: "#" },
  { label: "How it works", href: "#how-it-works" },
  { label: "About", href: "#about" },
  { label: "Privacy", href: "/privacy" },
];

export function NavLinks({
  resolveHref,
  onLinkClick,
  className = "",
  itemClassName = "",
}: NavLinksProps) {
  return (
    <div
      className={`hidden items-center gap-7 text-[0.95rem] font-medium text-mbiu-ink/90 md:flex lg:gap-9 dark:text-[#F6F2E9] ${className}`}
    >
      {DEFAULT_NAV_LINKS.map((link) => (
        <a
          key={link.label}
          href={resolveHref(link.href)}
          onClick={onLinkClick}
          className={`transition hover:text-mbiu-indigo dark:hover:text-white ${itemClassName}`}
        >
          {link.label}
        </a>
      ))}
    </div>
  );
}
