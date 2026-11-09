"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Footer } from "@/components/footer/Footer";
import { Hero } from "@/components/landing/hero/Hero";
import { Navbar } from "@/components/Navbar";
import { SiteBackdrop } from "@/components/SiteBackdrop";
import { StreamView } from "@/components/landing/stream/StreamView";
import { UploadArea } from "@/components/landing/UploadArea";
import { WorkSteps } from "@/components/landing/WorkSteps";
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

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileKey, setTurnstileKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [stream, setStream] = useState<EventStream | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [log, setLog] = useState(emptyLog);
  const [keptSince, setKeptSince] = useState<number | null>(null);
  const [toCheck, setToCheck] = useState<Clause[] | null>(null);
  const [resumeUnfinished, setResumeUnfinished] = useState(false);
  const [resultsStatus, setResultsStatus] = useState<string | null>(null);
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
    return (
      <StreamView
        stream={stream}
        selectedFile={selectedFile}
        isStreaming={isStreaming}
        keptSince={keptSince}
        clausesToCheck={clausesToCheck}
        unfinished={unfinished}
        resultsStatus={resultsStatus}
        turnstileKey={turnstileKey}
        onKeepChange={setKeep}
        onStartOver={startOver}
        onCheckClauses={checkClauses}
        onCheckUnfinished={() => setToCheck(unfinished)}
        onRetryClause={retryClause}
        onSecurityCheckError={() =>
          setResultsStatus("The security check could not load. Please try again.")
        }
      />
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <SiteBackdrop />
      <Navbar />

      <main className="relative z-10" id="hero">
        <Hero />

        <section
          id="how-it-works"
          className="mx-auto w-full max-w-[1280px] scroll-mt-20 px-4 pb-20 sm:scroll-mt-24 sm:px-8 sm:pb-24"
        >
          <div className="landing-upload w-full rounded-[28px] border border-white/70 bg-white/40 p-6 shadow-[0_36px_90px_-48px_rgba(22,26,38,0.55)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.05] sm:rounded-[36px] sm:p-10 md:p-12">
            <WorkSteps />

            <div className="my-10 h-px w-full bg-mbiu-ink/15 dark:bg-white/15 sm:my-12" />

            <UploadArea
              selectedFile={selectedFile}
              consentChecked={consentChecked}
              turnstileKey={turnstileKey}
              isUploading={isUploading}
              isSubmitEnabled={isSubmitEnabled}
              errorMessage={errorMessage}
              notice={notice}
              onFileSelect={handleFileSelect}
              onConsentChange={setConsentChecked}
              onTurnstileSuccess={setTurnstileToken}
              onTurnstileError={() =>
                setErrorMessage("The security check could not load. Please refresh the page.")
              }
              onTurnstileExpire={() => setTurnstileToken(null)}
              onUpload={handleUpload}
              onError={setErrorMessage}
            />
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
