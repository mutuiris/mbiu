"use client";

import React, { useState } from "react";

import { FileDropzone } from "@/components/FileDropzone";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { LiveResults } from "@/components/results/LiveResults";
import { Turnstile } from "@/components/Turnstile";
import { fetchEvaluationStream, type EvaluationEvent } from "@/lib/api/stream";
import { API_URL } from "@/lib/env";
import { validateContractFile } from "@/lib/validation";

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  // Tokens are single use, so a new key remounts the widget for a fresh one
  const [turnstileKey, setTurnstileKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [stream, setStream] = useState<AsyncGenerator<EvaluationEvent, void, unknown> | null>(
    null
  );

  const isSubmitEnabled =
    selectedFile !== null && consentChecked && Boolean(turnstileToken) && !isUploading;

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const resetTurnstile = () => {
    setTurnstileToken(null);
    setTurnstileKey((key) => key + 1);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !consentChecked || !turnstileToken) return;

    setErrorMessage(null);
    const validation = validateContractFile(selectedFile);
    if (!validation.valid) {
      setErrorMessage(validation.error);
      return;
    }

    setIsUploading(true);
    try {
      setStream(
        await fetchEvaluationStream({ file: selectedFile, turnstileToken, apiUrl: API_URL })
      );
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "An unexpected error occurred.");
      resetTurnstile();
    } finally {
      setIsUploading(false);
    }
  };

  const startOver = () => {
    setStream(null);
    resetTurnstile();
  };

  if (stream) {
    return (
      <main className="page-wrapper results-page">
        <div className="stream-controls">
          <button type="button" className="secondary-btn restart-btn" onClick={startOver}>
            Check another contract
          </button>
        </div>
        <LiveResults eventStream={stream} onRetryAll={startOver} file={selectedFile} />
      </main>
    );
  }

  return (
    <main className="page-wrapper">
      <header className="header-section">
        <h1 className="brand-title">Mbiu</h1>
        <p className="brand-tagline">Understand a music contract before you sign it.</p>
      </header>

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
