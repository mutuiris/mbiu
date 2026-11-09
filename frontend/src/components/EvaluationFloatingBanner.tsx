"use client";

import React, { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import {
  getActiveMemorySession,
  hasActiveEvaluationSession,
  subscribeMemorySession,
} from "@/lib/keep-tab";

export function EvaluationFloatingBanner() {
  const pathname = usePathname();
  const router = useRouter();
  const [hasSession, setHasSession] = useState(false);
  const [isViewingResults, setIsViewingResultsState] = useState(false);

  useEffect(() => {
    const update = () => {
      const active = hasActiveEvaluationSession();
      const memory = getActiveMemorySession();
      setHasSession(active);
      setIsViewingResultsState(Boolean(memory?.isViewingResults));
    };

    update();
    const unsub = subscribeMemorySession(update);
    const handleCustom = () => update();
    const handleStorage = () => update();

    window.addEventListener("mbiu-session-change", handleCustom);
    window.addEventListener("storage", handleStorage);

    return () => {
      unsub();
      window.removeEventListener("mbiu-session-change", handleCustom);
      window.removeEventListener("storage", handleStorage);
    };
  }, [pathname]);

  // Don't show if there's no active evaluation session,
  // or if the user is already on the homepage looking directly at the results.
  const isHome = pathname === "/";
  if (!hasSession || (isHome && isViewingResults)) {
    return null;
  }

  const handleReturnClick = () => {
    if (isHome) {
      window.dispatchEvent(new CustomEvent("mbiu-return-to-evaluation"));
    } else {
      router.push("/?view=results");
    }
  };

  return (
    <aside
      className="fixed top-20 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-[1120px] pointer-events-none transition-all duration-300"
      aria-label="Active contract evaluation notification"
    >
      <div className="pointer-events-auto flex items-center justify-between gap-3 rounded-2xl border border-mbiu-indigo/40 bg-white/95 px-4 py-2.5 shadow-[0_10px_35px_-5px_rgba(22,26,38,0.25)] backdrop-blur-md dark:border-white/20 dark:bg-[#101d24]/95">
        <div className="flex items-center gap-2.5 text-[0.88rem] sm:text-[0.92rem] font-medium text-mbiu-ink dark:text-[#F6F2E9]">
          <FileText className="h-4 w-4 text-mbiu-indigo shrink-0 dark:text-mbiu-peach" />
          <span>Your contract evaluation is still open in this tab.</span>
        </div>

        {isHome ? (
          <button
            type="button"
            onClick={handleReturnClick}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-mbiu-indigo px-4 py-1.5 text-[0.82rem] sm:text-[0.85rem] font-semibold text-white shadow-sm transition hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
          >
            <span>Return to evaluation</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        ) : (
          <Link
            href="/?view=results"
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-mbiu-indigo px-4 py-1.5 text-[0.82rem] sm:text-[0.85rem] font-semibold text-white shadow-sm transition hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
          >
            <span>Return to evaluation</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>
    </aside>
  );
}

