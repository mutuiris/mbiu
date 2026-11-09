"use client";

import React, { useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NavBrand } from "./NavBrand";
import { NavCta } from "./NavCta";
import { NavDrawer } from "./NavDrawer";
import { NavLinks } from "./NavLinks";

const emptySubscribe = () => () => {};

export interface NavbarProps {
  basePath?: string;
  onUploadClick?: () => void;
}

export function Navbar({ basePath = "", onUploadClick }: NavbarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const isClient = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );

  const resolveHref = (target: string) => {
    if (target.startsWith("#")) {
      return basePath ? `${basePath}${target}` : target;
    }
    if (!basePath || basePath === "/") {
      return target.startsWith("/") ? target : `/${target}`;
    }
    const cleanBase = basePath.endsWith("/") ? basePath.slice(0, -1) : basePath;
    const cleanTarget = target.startsWith("/") ? target : `/${target}`;
    return `${cleanBase}${cleanTarget}`;
  };

  const closeMenu = () => setIsOpen(false);

  return (
    <>
      <header className="sticky top-0 z-40 w-full bg-mbiu-cream/80 px-3 py-2.5 backdrop-blur-md transition-colors sm:px-6 sm:py-3 dark:bg-mbiu-bg-dark/80">
        <nav
          className="mx-auto flex max-w-[1280px] items-center justify-between rounded-full border border-[#d5c5b2] bg-[#fffdfa] px-3 py-2 shadow-[0_16px_40px_-16px_rgba(22,26,38,0.22),0_3px_10px_-2px_rgba(22,26,38,0.08)] backdrop-blur-xl dark:border-white/15 dark:bg-[#101d24] dark:shadow-[0_16px_40px_-12px_rgba(0,0,0,0.7)] sm:px-5 sm:py-2.5"
          aria-label="Main Navigation"
        >
          <NavBrand href={resolveHref("/")} onClick={closeMenu} />

          <NavLinks resolveHref={resolveHref} />

          <div className="flex shrink-0 items-center gap-2">
            <ThemeToggle />

            <NavCta href={resolveHref("#upload")} onClick={onUploadClick} />

            <button
              type="button"
              onClick={() => setIsOpen(!isOpen)}
              aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isOpen}
              aria-controls="mobile-menu"
              className="grid h-10 w-10 place-items-center rounded-full border border-mbiu-ink/20 bg-white text-mbiu-ink shadow-xs transition hover:border-mbiu-ink/40 hover:bg-[#faf7f2] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo md:hidden dark:border-white/20 dark:bg-white/[0.06] dark:text-[#F4EFE6] dark:hover:border-white/40 dark:hover:bg-white/10 dark:focus-visible:outline-mbiu-indigo-dark"
            >
              {isOpen ? (
                <X className="h-5 w-5" strokeWidth={2.2} />
              ) : (
                <Menu className="h-5 w-5" strokeWidth={2.2} />
              )}
            </button>
          </div>
        </nav>
      </header>

      {isClient && typeof document !== "undefined" && isOpen
        ? createPortal(
            <NavDrawer
              isOpen={isOpen}
              onClose={closeMenu}
              resolveHref={resolveHref}
              onUploadClick={onUploadClick}
            />,
            document.body
          )
        : null}
    </>
  );
}
