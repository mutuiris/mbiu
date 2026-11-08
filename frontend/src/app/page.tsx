"use client";

import {
  ArrowRight,
  CircleHelp,
  Diamond,
  Info,
  Lock,
  TriangleAlert,
} from "lucide-react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FileDropzone } from "@/components/FileDropzone";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { KeepResultsSwitch } from "@/components/results/KeepResultsSwitch";
import { LiveResults } from "@/components/results/LiveResults";
import { SiteBackdrop } from "@/components/SiteBackdrop";
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

function ClausePreviewCard() {
  return (
    <article className="relative z-10 w-full max-w-[380px] rounded-[24px] border border-white/70 bg-[#fbf1e1]/70 p-5 shadow-[0_36px_90px_-32px_rgba(30,25,15,0.5)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] dark:shadow-[0_36px_90px_-34px_rgba(0,0,0,0.9)] sm:rounded-[28px] sm:p-7 xl:mt-2">
      <div className="flex items-center gap-2.5">
        <Diamond className="h-3.5 w-3.5 fill-[#e98a3f] text-[#e98a3f]" strokeWidth={1} />
        <span className="text-[0.88rem] font-medium text-mbiu-ink dark:text-[#EDE7DB] sm:text-[0.9rem]">
          Clause 7.2
        </span>
      </div>

      <h2 className="mt-1 text-[1.35rem] font-extrabold leading-tight tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.55rem]">
        Post-term exclusivity
      </h2>

      <span className="mt-3 inline-flex items-center gap-2 rounded-full bg-mbiu-peach px-3.5 py-1.5 text-[0.82rem] font-bold text-mbiu-warning-text sm:px-4 sm:text-[0.88rem]">
        <TriangleAlert className="h-4 w-4 shrink-0 fill-[#c2410c] text-[#c2410c]" strokeWidth={1.5} />
        Worth inquiry
      </span>

      <p className="mt-4 font-serif text-[0.98rem] italic leading-6 text-mbiu-ink/90 dark:text-[#E7DFD2]/85 sm:text-[1.02rem] sm:leading-7">
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
          <p className="text-[0.88rem] font-bold leading-snug text-mbiu-ink dark:text-[#F6F2E9] sm:text-[0.9rem]">
            Could this affect your next opportunity?
          </p>
          <p className="mt-1.5 text-[0.85rem] leading-relaxed text-mbiu-ink/70 dark:text-[#B9C1C5] sm:text-[0.9rem]">
            “What happens if another label approaches me during this period?”
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2.5 border-t border-mbiu-ink/15 pt-4 text-[0.8rem] text-mbiu-ink/70 dark:border-white/15 dark:text-[#B9C1C5] sm:text-[0.82rem]">
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
      <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
        <SiteBackdrop variant="results" />
        <Navbar basePath="/" />

        <main className="results-page relative z-10 mx-auto w-full max-w-[880px] px-5 pb-20 pt-8 sm:px-8">
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

        <Footer basePath="/" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <SiteBackdrop />

      <Navbar />

      <main className="relative z-10" id="hero">
        <section
          id="about"
          className="mx-auto grid w-full max-w-[1280px] scroll-mt-20 items-center gap-8 px-4 pb-6 pt-4 sm:scroll-mt-24 sm:gap-10 sm:px-8 sm:pb-8 sm:pt-6 xl:grid-cols-[1.15fr_0.85fr] xl:gap-8 xl:pb-8 xl:pt-8"
        >
          <div className="mx-auto flex w-full max-w-[720px] flex-col items-center text-center xl:mx-0 xl:items-start xl:text-left">
            <h1 className="font-serif text-[clamp(2.15rem,5.5vw,4.5rem)] font-medium leading-[1.04] tracking-[-0.035em] text-mbiu-ink dark:text-[#F6F2E9] xl:leading-[0.92]">
              Understand your contract before you sign it.
            </h1>

            <p className="mt-5 text-[1.1rem] font-bold tracking-[-0.01em] text-mbiu-ink dark:text-[#F6F2E9] sm:mt-6 sm:text-[1.28rem]">
              Your music. Your rights. Your decisions.
            </p>
            <p className="mt-3 max-w-[480px] text-[0.95rem] leading-relaxed text-mbiu-ink/85 dark:text-[#B9C1C5] sm:mt-4 sm:text-[1.02rem] sm:leading-7">
              Upload your music contract and understand what you&apos;re agreeing to, what could
              affect you, and what questions to ask before signing.
            </p>

            <div className="mt-7 sm:mt-8 flex w-full justify-center xl:justify-start">
              <a
                href="#upload"
                className={`${primaryButton} h-[50px] w-full max-w-[320px] px-7 text-[0.98rem] sm:h-[52px] sm:w-auto sm:max-w-none sm:px-8 sm:text-[1.02rem]`}
              >
                Upload your contract
                <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2.2} />
              </a>
            </div>

            <p className="mt-4 flex items-center justify-center gap-2 text-[0.82rem] font-medium text-mbiu-ink/70 dark:text-[#B9C1C5] sm:mt-5 sm:text-[0.85rem] xl:justify-start">
              <Lock className="h-4 w-4 shrink-0" strokeWidth={2} />
              Mbiu does not store your contracts on our servers.
            </p>
          </div>

          <div className="flex w-full min-w-0 justify-center xl:justify-end xl:pr-14">
            <ClausePreviewCard />
          </div>
        </section>

        <section
          id="how-it-works"
          className="mx-auto w-full max-w-[1280px] scroll-mt-20 px-4 pb-20 sm:scroll-mt-24 sm:px-8 sm:pb-24"
        >
          <div className="landing-upload w-full rounded-[28px] border border-white/70 bg-white/40 p-6 shadow-[0_36px_90px_-48px_rgba(22,26,38,0.55)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.05] sm:rounded-[36px] sm:p-10 md:p-12">
            <div className="mx-auto flex max-w-[1120px] items-center gap-3 sm:gap-8">
              <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
              <h2 className="whitespace-nowrap font-serif text-[1.5rem] font-semibold italic tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.1rem]">
                How it works
              </h2>
              <div className="h-px flex-1 bg-mbiu-ink/25 dark:bg-white/20" />
            </div>

            <ol className="mx-auto mt-8 grid max-w-[980px] gap-6 sm:mt-10 sm:grid-cols-3 sm:gap-0">
              {steps.map((step, index) => (
                <li
                  key={step.number}
                  className={`flex items-center gap-4 sm:px-6 md:px-7 ${
                    index > 0 ? "sm:border-l sm:border-mbiu-ink/20 dark:sm:border-white/15" : ""
                  }`}
                >
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-mbiu-peach-strong text-[1.05rem] font-semibold text-[#1b2430] sm:h-14 sm:w-14 sm:text-[1.15rem]">
                    {step.number}
                  </span>
                  <div>
                    <p className="text-[0.98rem] font-semibold leading-tight text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.02rem]">
                      {step.title}
                    </p>
                    <p className="text-[0.98rem] leading-tight text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.02rem]">
                      {step.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>

            <div className="my-10 h-px w-full bg-mbiu-ink/15 dark:bg-white/15 sm:my-12" />

            <div id="upload" className="mx-auto w-full max-w-[880px] scroll-mt-28">
              <h3 className="font-serif text-[1.65rem] font-semibold tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2rem]">
                Upload your contract
              </h3>
              <p className="mt-2 text-[0.92rem] text-mbiu-ink/70 dark:text-[#B9C1C5] sm:text-[0.95rem]">
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
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
