"use client";

import React, { useState, useEffect, useRef, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import Image from "next/image";
import { ArrowRight, Menu, X } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

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
  const menuRef = useRef<HTMLDivElement>(null);
  const href = (hash: string) => `${basePath}${hash}`;

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

  // Lock body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Close menu when clicking outside the drawer
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

  const drawerElement = isOpen && (
    <div className="fixed inset-0 z-[9999] md:hidden">
      {/* High-opacity Backdrop Dimmer */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={closeMenu}
        aria-hidden="true"
      />

      {/* Slide-over Panel from Right using the exact body background color */}
      <div
        id="mobile-menu"
        ref={menuRef}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile Navigation"
        className="fixed inset-y-0 right-0 z-[10000] flex h-full w-[300px] max-w-[85vw] flex-col border-l border-mbiu-ink/15 bg-mbiu-cream p-6 shadow-[0_0_60px_rgba(0,0,0,0.6)] transition-transform dark:border-white/15 dark:bg-mbiu-bg-dark"
      >
        {/* Drawer Header: Logo on left, Close button on right */}
        <div className="flex items-center justify-between">
          <a
            href={basePath || "#"}
            className="flex items-center gap-1.5 transition hover:opacity-90"
            onClick={closeMenu}
          >
            <Image
              src="/brand/mbiu-horn.png"
              alt=""
              width={972}
              height={590}
              priority
              className="h-8 w-auto dark:invert object-contain"
            />
            <span className="text-[1.2rem] font-extrabold tracking-[-0.06em] leading-none text-mbiu-ink dark:text-[#F6F2E9]">
              mbiu
            </span>
          </a>

          <button
            type="button"
            onClick={closeMenu}
            aria-label="Close navigation menu"
            className="grid h-9 w-9 place-items-center rounded-lg border border-mbiu-ink/20 text-mbiu-ink transition hover:border-mbiu-ink/40 hover:bg-black/5 focus-visible:outline-2 dark:border-white/20 dark:text-[#F4EFE6] dark:hover:border-white/40 dark:hover:bg-white/10"
          >
            <X className="h-5 w-5" strokeWidth={2} />
          </button>
        </div>

        {/* Subtle Divider Line below header */}
        <div className="my-5 h-px w-full bg-mbiu-ink/10 dark:bg-white/10" />

        {/* Vertical Navigation Links (Clean plain-text stacked list) */}
        <nav className="flex flex-col gap-5 py-2 text-[1rem] font-medium text-mbiu-ink dark:text-[#F6F2E9]">
          <a
            href={href("#")}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            Home
          </a>

          <a
            href={href("#how-it-works")}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            How it works
          </a>

          <a
            href={href("#privacy")}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            Privacy
          </a>

          <a
            href={href("#about")}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            About
          </a>

          <a
            href={basePath ? `${basePath}/terms` : "/terms"}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            Terms of Service
          </a>

          <a
            href={basePath ? `${basePath}/privacy` : "/privacy"}
            onClick={closeMenu}
            className="transition hover:text-mbiu-indigo dark:hover:text-white"
          >
            Privacy Policy
          </a>
        </nav>

        {/* Drawer Bottom CTA */}
        <div className="mt-auto border-t border-mbiu-ink/10 pt-6 dark:border-white/10">
          <a
            href={href("#upload")}
            onClick={closeMenu}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-5 text-[0.92rem] font-semibold text-white shadow-md transition hover:bg-mbiu-indigo-hover focus-visible:outline-2 dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea]"
          >
            <span>Upload your contract</span>
            <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
          </a>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <header className="sticky top-0 z-40 w-full bg-mbiu-cream/80 px-3 py-2.5 backdrop-blur-md transition-colors sm:px-6 sm:py-3 dark:bg-mbiu-bg-dark/80">
        <nav
          className="mx-auto flex max-w-[1280px] items-center justify-between rounded-full border border-[#d5c5b2] bg-[#fffdfa] px-3 py-2 shadow-[0_16px_40px_-16px_rgba(22,26,38,0.22),0_3px_10px_-2px_rgba(22,26,38,0.08)] backdrop-blur-xl dark:border-white/15 dark:bg-[#101d24] dark:shadow-[0_16px_40px_-12px_rgba(0,0,0,0.7)] sm:px-5 sm:py-2.5"
          aria-label="Main Navigation"
        >
          {/* Brand Logo */}
          <a
            href={basePath || "#"}
            className="flex shrink-0 items-center gap-1 sm:gap-1.5 pl-0.5 transition hover:opacity-90"
            aria-label="Mbiu home"
            onClick={closeMenu}
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

          {/* Desktop Navigation Links */}
          <div className="hidden items-center gap-7 text-[0.95rem] font-medium text-mbiu-ink/90 md:flex lg:gap-9 dark:text-[#F6F2E9]">
            <a
              href={href("#how-it-works")}
              className="transition hover:text-mbiu-indigo dark:hover:text-white"
            >
              How it works
            </a>
            <a
              href={href("#privacy")}
              className="transition hover:text-mbiu-indigo dark:hover:text-white"
            >
              Privacy
            </a>
            <a
              href={href("#about")}
              className="transition hover:text-mbiu-indigo dark:hover:text-white"
            >
              About
            </a>
          </div>

          {/* Right Side Controls */}
          <div className="flex shrink-0 items-center gap-2">
            <ThemeToggle />

            {/* Desktop CTA Button */}
            <div className="hidden md:block rounded-full bg-mbiu-ink/[0.04] p-1 dark:bg-white/[0.05]">
              <a
                href={href("#upload")}
                onClick={onUploadClick}
                className="inline-flex h-10 lg:h-11 items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-4 lg:px-6 text-[0.9rem] font-semibold text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea] dark:focus-visible:outline-mbiu-indigo-dark"
              >
                <span>Upload your contract</span>
                <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
              </a>
            </div>

            {/* Mobile Menu Trigger Button */}
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

      {/* Render drawer via React Portal to document.body for clean stacking & full opacity */}
      {isClient && typeof document !== "undefined" && drawerElement
        ? createPortal(drawerElement, document.body)
        : null}
    </>
  );
}
