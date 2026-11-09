import React, { useEffect, useRef } from "react";
import Image from "next/image";
import { ArrowRight, X } from "lucide-react";
import { DEFAULT_NAV_LINKS } from "./NavLinks";

export interface NavDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  resolveHref: (target: string) => string;
  onUploadClick?: () => void;
}

export function NavDrawer({
  isOpen,
  onClose,
  resolveHref,
  onUploadClick,
}: NavDrawerProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] md:hidden">
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        id="mobile-menu"
        ref={menuRef}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile Navigation"
        className="fixed inset-y-0 right-0 z-[10000] flex h-full w-[300px] max-w-[85vw] flex-col border-l border-mbiu-ink/15 bg-mbiu-cream p-6 shadow-[0_0_60px_rgba(0,0,0,0.6)] transition-transform dark:border-white/15 dark:bg-mbiu-bg-dark"
      >
        <div className="flex items-center justify-between">
          <a
            href={resolveHref("/")}
            className="flex items-center gap-1.5 transition hover:opacity-90"
            onClick={onClose}
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
            onClick={onClose}
            aria-label="Close navigation menu"
            className="grid h-9 w-9 place-items-center rounded-lg border border-mbiu-ink/20 text-mbiu-ink transition hover:border-mbiu-ink/40 hover:bg-black/5 focus-visible:outline-2 dark:border-white/20 dark:text-[#F4EFE6] dark:hover:border-white/40 dark:hover:bg-white/10"
          >
            <X className="h-5 w-5" strokeWidth={2} />
          </button>
        </div>

        <div className="my-5 h-px w-full bg-mbiu-ink/10 dark:bg-white/10" />

        <nav className="flex flex-col gap-5 py-2 text-[1rem] font-medium text-mbiu-ink dark:text-[#F6F2E9]">
          {DEFAULT_NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={resolveHref(link.href)}
              onClick={onClose}
              className="transition hover:text-mbiu-indigo dark:hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="mt-auto pt-6 border-t border-mbiu-ink/10 dark:border-white/10">
          <a
            href={resolveHref("#upload")}
            onClick={() => {
              onClose();
              onUploadClick?.();
            }}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-5 text-[0.92rem] font-semibold text-white shadow-md transition hover:bg-mbiu-indigo-hover focus-visible:outline-2 dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea]"
          >
            <span>Upload your contract</span>
            <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
          </a>
        </div>
      </div>
    </div>
  );
}
