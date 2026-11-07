"use client";

import {
  ArrowRight,
  CircleHelp,
  Diamond,
  Info,
  Lock,
  Music,
  Music2,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import Image from "next/image";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FileDropzone } from "@/components/FileDropzone";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { KeepResultsSwitch } from "@/components/results/KeepResultsSwitch";
import { LiveResults } from "@/components/results/LiveResults";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Turnstile } from "@/components/Turnstile";
import type { Clause } from "@/lib/api/generated/types.gen";
import {
  fetchClauseEvaluations,
  fetchEvaluationStream,
  type EvaluationEvent,
} from "@/lib/api/stream";
import { API_URL } from "@/lib/env";
import {
  KEEP_FOR_MS,
  NOT_SAVED_MESSAGE,
  clearKeptResults,
  forgetResults,
  keepResults,
  markResultsShown,
  restoreResults,
  resultsWereShown,
} from "@/lib/keep-tab";
import { emptyLog, replay, tracked, unfinishedClauses, withEvent } from "@/lib/results-log";
import { validateContractFile } from "@/lib/validation";

type EventStream = AsyncGenerator<EvaluationEvent, void, unknown>;

const steps = [
  { number: "01", title: "Upload", body: "your contract." },
  { number: "02", title: "Understand", body: "each clause." },
  { number: "03", title: "Take your questions", body: "to the table." },
];

const primaryButton =
  "inline-flex items-center justify-center gap-2.5 rounded-full bg-mbiu-indigo text-white shadow-[0_18px_36px_-18px_rgba(38,41,140,0.85)] transition hover:-translate-y-0.5 hover:bg-mbiu-indigo-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:bg-mbiu-indigo-dark dark:hover:bg-[#6b74ea] dark:focus-visible:outline-mbiu-indigo-dark";

function Rays({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 84 92" fill="none" className={className}>
      <path d="M36 88 20 36" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
      <path d="M54 78V20" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
      <path d="m70 84 12-42" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
    </svg>
  );
}

function TribalPattern({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 260" fill="none" className={className}>
      <path d="M-36 252 54 132l94 120" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-62 240 54 96l120 144" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-40 216 54 60l104 156" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-14 224 54 148l70 76" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <circle cx="54" cy="132" r="3.5" fill="currentColor" />
      <circle cx="54" cy="96" r="3.5" fill="currentColor" />
      <circle cx="54" cy="60" r="3.5" fill="currentColor" />
      <circle cx="118" cy="118" r="3" fill="currentColor" />
      <circle cx="150" cy="168" r="3" fill="currentColor" />
    </svg>
  );
}

function Backdrop() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-[100svh] min-h-[720px] max-h-[1000px] overflow-hidden"
    >
      <Image
        src="/brand/mbiu-horn-watermark.png"
        alt=""
        width={972}
        height={590}
        priority
        className="absolute left-1/2 top-[30%] w-[185%] max-w-none -translate-x-1/2 opacity-45 mix-blend-multiply sm:top-[10%] sm:w-[128%] lg:left-auto lg:right-[9%] lg:top-[8%] lg:w-[60%] lg:translate-x-0 lg:opacity-60 dark:opacity-[0.08] dark:invert dark:mix-blend-screen"
      />

      <Rays className="absolute left-[2%] top-[13%] hidden h-[62px] w-[58px] text-mbiu-ink sm:block dark:text-white/70" />
      <TribalPattern className="absolute -bottom-8 -left-8 h-[220px] w-[190px] text-mbiu-ink sm:h-[260px] sm:w-[225px] dark:text-white/60" />

      <Music2 className="absolute right-[6%] top-[10%] h-9 w-9 rotate-[10deg] text-mbiu-ink/90 dark:text-white/70 lg:right-[11%] lg:top-[20%]" />
      <Music2 className="absolute bottom-[7%] right-[7%] h-10 w-10 rotate-[14deg] text-mbiu-ink/90 dark:text-white/70" />
      <Music className="absolute bottom-[3%] right-[3%] h-7 w-7 -rotate-[12deg] text-mbiu-ink/80 dark:text-white/60" />
      <Sparkles className="absolute bottom-[11%] right-[2%] h-5 w-5 text-mbiu-ink/60 dark:text-white/50" />
    </div>
  );
}

function ClausePreviewCard() {
  return (
    <article className="relative z-10 w-full max-w-[380px] rounded-[28px] border border-white/70 bg-[#fbf1e1]/70 p-6 shadow-[0_36px_90px_-32px_rgba(30,25,15,0.5)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] dark:shadow-[0_36px_90px_-34px_rgba(0,0,0,0.9)] sm:p-7 lg:mt-8">
      <div className="flex items-center gap-2.5">
        <Diamond className="h-3.5 w-3.5 fill-[#e98a3f] text-[#e98a3f]" strokeWidth={1} />
        <span className="text-[0.9rem] font-medium text-mbiu-ink dark:text-[#EDE7DB]">
          Clause 7.2
        </span>
      </div>

      <h2 className="mt-1 text-[1.45rem] font-extrabold leading-tight tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.55rem]">
        Post-term exclusivity
      </h2>

      <span className="mt-3 inline-flex items-center gap-2 rounded-full bg-mbiu-peach px-4 py-1.5 text-[0.88rem] font-bold text-mbiu-warning-text">
        <TriangleAlert className="h-4 w-4 fill-[#c2410c] text-[#c2410c]" strokeWidth={1.5} />
        Worth inquiry
      </span>

      <p className="mt-4 font-serif text-[1.02rem] italic leading-7 text-mbiu-ink/90 dark:text-[#E7DFD2]/85">
        “Your agreement could restrict you from working with other labels for two years after it
        ends.”
      </p>

      <div className="my-4 h-px w-full bg-mbiu-ink/15 dark:bg-white/15" />

      <div className="flex gap-3">
        <CircleHelp
          className="mt-0.5 h-5 w-5 shrink-0 text-mbiu-ink dark:text-[#EDE7DB]"
          strokeWidth={1.8}
        />
        <div>
          <p className="text-[0.9rem] font-bold leading-snug text-mbiu-ink dark:text-[#F6F2E9]">
            Could this affect your next opportunity?
          </p>
          <p className="mt-1.5 text-[0.9rem] leading-relaxed text-mbiu-ink/70 dark:text-[#B9C1C5]">
            “What happens if another label approaches me during this period?”
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2.5 border-t border-mbiu-ink/15 pt-4 text-[0.82rem] text-mbiu-ink/70 dark:border-white/15 dark:text-[#B9C1C5]">
        <Info className="h-[18px] w-[18px] shrink-0" strokeWidth={1.8} />
        This isn&apos;t legal advice.
      </div>
    </article>
  );
}

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  // Tokens are single use, so a new key remounts the widget for a fresh one
  const [turnstileKey, setTurnstileKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [stream, setStream] = useState<EventStream | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [log, setLog] = useState(emptyLog);
  const [keptSince, setKeptSince] = useState<number | null>(null);
  // Clauses waiting for a bot check before they're sent; resumeUnfinished picks them all
  const [toCheck, setToCheck] = useState<Clause[] | null>(null);
  const [resumeUnfinished, setResumeUnfinished] = useState(false);
  const [resultsStatus, setResultsStatus] = useState<string | null>(null);
  // Ends of streams that were replaced or abandoned are ignored
  const generation = useRef(0);

  const unfinished = useMemo(() => unfinishedClauses(log), [log]);
  const clausesToCheck = toCheck ?? (resumeUnfinished && unfinished.length ? unfinished : null);

  const isSubmitEnabled =
    selectedFile !== null && consentChecked && Boolean(turnstileToken) && !isUploading;

  const resetTurnstile = () => {
    setTurnstileToken(null);
    setTurnstileKey((key) => key + 1);
  };

  const startStream = useCallback((source: EventStream, resumeIfDropped: boolean) => {
    const id = ++generation.current;
    setIsStreaming(true);
    setStream(
      tracked(
        source,
        (event) => setLog((current) => withEvent(current, event)),
        ({ complete, sawDone }) => {
          if (id !== generation.current) return;
          setIsStreaming(false);
          if (complete && (sawDone || !resumeIfDropped)) return;
          setResumeUnfinished(resumeIfDropped);
          setResultsStatus(
            resumeIfDropped
              ? "The connection dropped. Mbiu will check any unfinished clauses again."
              : "The connection dropped again. Your results so far are below."
          );
        }
      )
    );
  }, []);

  useEffect(() => {
    // sessionStorage exists only in the browser, so this waits until after hydration
    void Promise.resolve().then(() => {
      const kept = restoreResults();
      if (kept) {
        setKeptSince(kept.keptSince);
        setResumeUnfinished(true);
        startStream(replay(kept.events), false);
      } else if (resultsWereShown()) {
        forgetResults();
        setNotice(NOT_SAVED_MESSAGE);
      }
    });
  }, [startStream]);

  useEffect(() => {
    if (!stream) return;
    markResultsShown();
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [stream]);

  useEffect(() => {
    if (keptSince !== null) keepResults({ keptSince, events: [...log.values()] });
  }, [keptSince, log]);

  useEffect(() => {
    if (keptSince === null) return;
    const timer = setTimeout(() => {
      clearKeptResults();
      setKeptSince(null);
      setResultsStatus("An hour has passed, so this device no longer keeps your results.");
    }, keptSince + KEEP_FOR_MS - Date.now());
    return () => clearTimeout(timer);
  }, [keptSince]);

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !consentChecked || !turnstileToken) return;

    setErrorMessage(null);
    setNotice(null);
    const validation = validateContractFile(selectedFile);
    if (!validation.valid) {
      setErrorMessage(validation.error);
      return;
    }

    setIsUploading(true);
    try {
      const source = await fetchEvaluationStream({
        file: selectedFile,
        turnstileToken,
        apiUrl: API_URL,
      });
      setLog(emptyLog);
      startStream(source, true);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "An unexpected error occurred.");
      resetTurnstile();
    } finally {
      setIsUploading(false);
    }
  };

  const checkClauses = async (token: string) => {
    if (!clausesToCheck) return;
    setToCheck(null);
    setResumeUnfinished(false);
    setResultsStatus(null);
    setIsStreaming(true);
    resetTurnstile();
    try {
      startStream(
        await fetchClauseEvaluations({ clauses: clausesToCheck, turnstileToken: token, apiUrl: API_URL }),
        false
      );
    } catch (err) {
      setIsStreaming(false);
      setResultsStatus(err instanceof Error ? err.message : "An unexpected error occurred.");
    }
  };

  const retryClause = (clauseId: string) => {
    const clause = unfinished.find((c) => c.clause_id === clauseId);
    if (clause) setToCheck([clause]);
  };

  const setKeep = (keep: boolean) => {
    if (!keep) {
      clearKeptResults();
      setKeptSince(null);
      return;
    }
    const now = Date.now();
    if (keepResults({ keptSince: now, events: [...log.values()] })) {
      setKeptSince(now);
    } else {
      setResultsStatus("This browser won't keep results, so they stay only while this page is open.");
    }
  };

  const startOver = () => {
    generation.current++;
    forgetResults();
    setStream(null);
    setIsStreaming(false);
    setLog(emptyLog);
    setKeptSince(null);
    setToCheck(null);
    setResumeUnfinished(false);
    setResultsStatus(null);
    resetTurnstile();
  };

  if (stream) {
    const isIdle = !isStreaming && !clausesToCheck;
    return (
      <main className="page-wrapper results-page">
        <div className="stream-controls">
          <button type="button" className="secondary-btn restart-btn" onClick={startOver}>
            Check another contract
          </button>
        </div>
        <KeepResultsSwitch kept={keptSince !== null} onChange={setKeep} />
        <div className="resume-panel" role="status" aria-live="polite">
          {resultsStatus && <p>{resultsStatus}</p>}
          {!isStreaming && clausesToCheck && (
            <>
              <p>
                Checking {clausesToCheck.length === 1 ? "1 clause" : `${clausesToCheck.length} clauses`}{" "}
                again after a quick security check.
              </p>
              <Turnstile
                key={turnstileKey}
                onSuccess={checkClauses}
                onError={() =>
                  setResultsStatus("The security check could not load. Please try again.")
                }
              />
            </>
          )}
        </div>
        {isIdle && unfinished.length > 0 && (
          <button type="button" className="secondary-btn" onClick={() => setToCheck(unfinished)}>
            Check the {unfinished.length === 1 ? "unfinished clause" : `${unfinished.length} unfinished clauses`}
          </button>
        )}
        <LiveResults
          eventStream={stream}
          onRetryAll={startOver}
          onRetryClause={isIdle ? retryClause : undefined}
          file={selectedFile}
        />
      </main>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Backdrop />

      <header className="relative z-20 px-4 pt-5 sm:px-6">
        <nav className="mx-auto grid max-w-[1280px] grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-full border border-white/60 bg-white/45 px-3 py-2.5 shadow-[0_20px_60px_-36px_rgba(22,26,38,0.6)] backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.06] sm:px-4">
          <a href="#" className="flex shrink-0 items-center gap-2 pl-1" aria-label="Mbiu home">
            <Image
              src="/brand/mbiu-horn.png"
              alt=""
              width={972}
              height={590}
              priority
              className="h-8 w-auto dark:invert"
            />
            <span className="text-[1.6rem] font-extrabold tracking-[-0.06em] text-mbiu-ink dark:text-[#F6F2E9]">
              mbiu
            </span>
          </a>

          <div className="hidden items-center gap-9 text-[0.95rem] font-medium text-mbiu-ink/90 dark:text-[#E7E0D4]/85 md:flex">
            <a
              href="#how-it-works"
              className="transition hover:text-mbiu-indigo dark:hover:text-white"
            >
              How it works
            </a>
            <a href="#privacy" className="transition hover:text-mbiu-indigo dark:hover:text-white">
              Privacy
            </a>
            <a href="#about" className="transition hover:text-mbiu-indigo dark:hover:text-white">
              About
            </a>
          </div>

          <div className="flex shrink-0 items-center gap-2 justify-self-end">
            <ThemeToggle />
            <div className="rounded-full bg-white/40 p-1 dark:bg-white/[0.04]">
              <a
                href="#upload"
                className={`${primaryButton} h-11 px-4 text-[0.92rem] font-semibold sm:px-6`}
              >
                <span className="hidden sm:inline">Upload your contract</span>
                <span className="sm:hidden">Upload</span>
                <ArrowRight className="h-4 w-4" strokeWidth={2.2} />
              </a>
            </div>
          </div>
        </nav>
      </header>

      <main className="relative z-10">
        <section
          id="about"
          className="mx-auto grid w-full max-w-[1280px] items-center gap-10 px-5 pb-12 pt-12 sm:px-8 sm:pt-16 lg:grid-cols-[1.1fr_0.9fr] lg:gap-6 lg:pb-10 lg:pt-20"
        >
          <div className="min-w-0 max-w-[660px]">
            <h1 className="font-serif text-[clamp(2.9rem,6vw,5rem)] font-medium leading-[0.88] tracking-[-0.04em] text-mbiu-ink dark:text-[#F6F2E9]">
              Understand your contract before you sign it.
            </h1>

            <p className="mt-7 text-[1.15rem] font-bold tracking-[-0.01em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.28rem]">
              Your music. Your rights. Your decisions.
            </p>
            <p className="mt-4 max-w-[430px] text-[0.98rem] leading-7 text-mbiu-ink/85 dark:text-[#B9C1C5] sm:text-[1.02rem]">
              Upload your music contract and understand what you&apos;re agreeing to, what could
              affect you, and what questions to ask before signing.
            </p>

            <div className="mt-8">
              <a href="#upload" className={`${primaryButton} h-[52px] px-8 text-[1.02rem]`}>
                Upload your contract
                <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2.2} />
              </a>
            </div>

            <p className="mt-5 flex items-center gap-2 text-[0.85rem] font-medium text-mbiu-ink/70 dark:text-[#B9C1C5]">
              <Lock className="h-4 w-4" strokeWidth={2} />
              Your contract isn&apos;t stored on our servers.
            </p>
          </div>

          <div className="flex min-w-0 justify-center lg:justify-end lg:pr-16">
            <ClausePreviewCard />
          </div>
        </section>

        <section
          id="how-it-works"
          className="mx-auto w-full max-w-[1280px] px-5 pb-16 sm:px-8"
        >
          <div className="mx-auto flex max-w-[1120px] items-center gap-5 sm:gap-8">
            <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
            <h2 className="whitespace-nowrap font-serif text-[1.9rem] font-semibold italic tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.1rem]">
              How it works
            </h2>
            <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
          </div>

          <ol className="mx-auto mt-10 grid max-w-[980px] gap-8 sm:grid-cols-3 sm:gap-0">
            {steps.map((step, index) => (
              <li
                key={step.number}
                className={`flex items-center gap-4 sm:px-7 ${
                  index > 0 ? "sm:border-l sm:border-mbiu-ink/20 dark:sm:border-white/15" : ""
                }`}
              >
                <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-mbiu-peach-strong text-[1.15rem] font-semibold text-[#1b2430]">
                  {step.number}
                </span>
                <div>
                  <p className="text-[1.02rem] font-semibold leading-tight text-mbiu-ink dark:text-[#F6F2E9]">
                    {step.title}
                  </p>
                  <p className="text-[1.02rem] leading-tight text-mbiu-ink dark:text-[#F6F2E9]">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section id="upload" className="mx-auto w-full max-w-[880px] px-5 pb-24 sm:px-8">
          <div className="landing-upload rounded-[32px] border border-white/70 bg-white/40 p-5 shadow-[0_36px_90px_-48px_rgba(22,26,38,0.55)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.05] sm:p-8">
            <h2 className="font-serif text-[2rem] font-semibold tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9]">
              Upload your contract
            </h2>
            <p className="mt-2 text-[0.95rem] text-mbiu-ink/70 dark:text-[#B9C1C5]">
              We read it once, explain each clause, and give you the questions to ask.
            </p>

            {notice && (
              <div className="status-alert info mt-6" role="status">
                {notice}
              </div>
            )}

            <form onSubmit={handleUpload} className="mt-6">
              <div id="privacy" className="scroll-mt-28">
                <PrivacyNotice consentChecked={consentChecked} onConsentChange={setConsentChecked} />
              </div>

              <FileDropzone
                selectedFile={selectedFile}
                onFileSelect={handleFileSelect}
                onError={setErrorMessage}
                disabled={isUploading}
              />

              <div className="turnstile-wrapper">
                <Turnstile
                  key={turnstileKey}
                  onSuccess={setTurnstileToken}
                  onError={() =>
                    setErrorMessage("The security check could not load. Please refresh the page.")
                  }
                  onExpire={() => setTurnstileToken(null)}
                />
              </div>

              {errorMessage && (
                <div className="status-alert error" role="alert">
                  <strong>Error: </strong>
                  {errorMessage}
                </div>
              )}

              <div className="action-section">
                <button type="submit" className="submit-btn" disabled={!isSubmitEnabled}>
                  {isUploading && <span className="spinner" />}
                  {isUploading ? "Uploading contract…" : "Check my contract"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
}
