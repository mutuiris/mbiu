"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { ArrowRight, Menu, X } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

interface NavbarProps {
  onUploadClick?: () => void;
}

export function Navbar({ onUploadClick }: NavbarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const closeMenu = () => setIsOpen(false);

  return (
    <header className="relative z-30 px-3 pt-3 sm:px-6 sm:pt-5" ref={menuRef}>
      <nav
        className="mx-auto flex max-w-[1280px] items-center justify-between rounded-full border border-white/60 bg-white/45 px-3 py-2 shadow-[0_20px_60px_-36px_rgba(22,26,38,0.6)] backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.06] sm:px-5 sm:py-2.5"
        aria-label="Main Navigation"
      >
        {/* Brand Logo */}
        <a
          href="#"
          className="flex shrink-0 items-center gap-2 pl-1 transition hover:opacity-90"
          aria-label="Mbiu home"
          onClick={closeMenu}
        >
          <Image
            src="/brand/mbiu-horn.png"
            alt=""
            width={972}
            height={590}
            priority
            className="h-7 w-auto sm:h-8 dark:invert"
          />
          <span className="text-[1.4rem] font-extrabold tracking-[-0.06em] text-mbiu-ink sm:text-[1.6rem] dark:text-[#F6F2E9]">
            mbiu
          </span>
        </a>

        {/* Desktop Navigation Links */}
        <div className="hidden items-center gap-7 text-[0.95rem] font-medium text-mbiu-ink/90 md:flex lg:gap-9 dark:text-[#E7E0D4]/85">
          <a
            href="#how-it-works"
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            How it works
          </a>
          <a
            href="#privacy"
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            Privacy
          </a>
          <a
            href="#about"
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            About
          </a>
        </div>

        {/* Right Side Controls */}
        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />

          {/* Desktop CTA Button */}
          <div className="hidden md:block rounded-full bg-white/40 p-1 dark:bg-white/[0.04]">
            <a
              href="#upload"
              onClick={onUploadClick}
              className="inline-flex h-10 lg:h-11 items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-4 lg:px-6 text-[0.9rem] font-semibold text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea] dark:focus-visible:outline-mbiu-indigo-dark"
            >
              <span>Upload your contract</span>
              <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
            </a>
          </div>

          {/* Mobile 3-Lines Hamburger Button */}
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={isOpen}
            className="grid h-10 w-10 place-items-center rounded-full border border-mbiu-ink/10 bg-white/50 text-mbiu-ink transition hover:bg-white/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo md:hidden dark:border-white/10 dark:bg-white/5 dark:text-[#F4EFE6] dark:hover:bg-white/10 dark:focus-visible:outline-mbiu-indigo-dark"
          >
            {isOpen ? (
              <X className="h-5 w-5" strokeWidth={2.2} />
            ) : (
              <Menu className="h-5 w-5" strokeWidth={2.2} />
            )}
          </button>
        </div>
      </nav>

      {/* Mobile Drawer / Dropdown Menu */}
      {isOpen && (
        <div
          className="mt-2 rounded-[24px] border border-white/70 bg-[#fbf5eb]/95 p-4 shadow-[0_24px_50px_-15px_rgba(22,26,38,0.35)] backdrop-blur-2xl md:hidden dark:border-white/15 dark:bg-[#0e1d24]/95 sm:p-5"
          role="dialog"
          aria-label="Mobile Navigation"
        >
          <div className="flex flex-col gap-2.5">
            <a
              href="#how-it-works"
              onClick={closeMenu}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-[1rem] font-semibold text-mbiu-ink transition hover:bg-black/5 dark:text-[#F6F2E9] dark:hover:bg-white/10"
            >
              <span>How it works</span>
              <ArrowRight className="h-4 w-4 opacity-50" />
            </a>

            <a
              href="#privacy"
              onClick={closeMenu}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-[1rem] font-semibold text-mbiu-ink transition hover:bg-black/5 dark:text-[#F6F2E9] dark:hover:bg-white/10"
            >
              <span>Privacy</span>
              <ArrowRight className="h-4 w-4 opacity-50" />
            </a>

            <a
              href="#about"
              onClick={closeMenu}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-[1rem] font-semibold text-mbiu-ink transition hover:bg-black/5 dark:text-[#F6F2E9] dark:hover:bg-white/10"
            >
              <span>About</span>
              <ArrowRight className="h-4 w-4 opacity-50" />
            </a>

            <div className="my-1.5 h-px w-full bg-mbiu-ink/10 dark:bg-white/10" />

            {/* Mobile Upload CTA */}
            <a
              href="#upload"
              onClick={closeMenu}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-5 text-[0.98rem] font-bold text-white shadow-lg transition hover:bg-mbiu-indigo-hover focus-visible:outline-2 dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea]"
            >
              <span>Upload your contract</span>
              <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
