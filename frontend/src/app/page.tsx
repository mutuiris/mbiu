"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FileDropzone } from "@/components/FileDropzone";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { KeepResultsSwitch } from "@/components/results/KeepResultsSwitch";
import { LiveResults } from "@/components/results/LiveResults";
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
    <main className="page-wrapper">
      <header className="header-section">
        <h1 className="brand-title">Mbiu</h1>
        <p className="brand-tagline">Understand a music contract before you sign it.</p>
      </header>

      {notice && (
        <div className="status-alert info" role="status">
          {notice}
        </div>
      )}

      <form onSubmit={handleUpload}>
        <PrivacyNotice consentChecked={consentChecked} onConsentChange={setConsentChecked} />

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
    </main>
  );
}
