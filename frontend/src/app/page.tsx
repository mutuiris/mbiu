"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { FileDropzone } from "@/components/FileDropzone";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { Turnstile } from "@/components/Turnstile";
import { API_URL } from "@/lib/env";
import { validateContractFile } from "@/lib/validation";

type UploadState = "idle" | "validating" | "uploading" | "error" | "done";

export default function Home() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const isSubmitEnabled =
    selectedFile !== null &&
    consentChecked &&
    Boolean(turnstileToken) &&
    uploadState === "idle";

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !consentChecked || !turnstileToken) return;

    setUploadState("validating");
    setErrorMessage(null);

    const validation = validateContractFile(selectedFile);
    if (!validation.valid) {
      setErrorMessage(validation.error);
      setUploadState("idle");
      return;
    }

    setUploadState("uploading");
    setStatusMessage("Connecting to evaluation stream...");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("turnstile_token", turnstileToken);

      const response = await fetch(`${API_URL}/api/v1/evaluations`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 404 || response.status === 502) {
          // Backend API is not yet running or MB-05 is pending
          setStatusMessage(
            "Evaluation pipeline skeleton ready. Waiting for live stream endpoint (MB-05)."
          );
          setUploadState("done");
          router.push("/results");
          return;
        }

        const errData = await response.json().catch(() => null);
        throw new Error(
          errData?.detail ||
            `Upload error (${response.status}): Mbiu could not process this contract right now.`
        );
      }

      setStatusMessage("Contract received! Evaluation stream starting...");
      setUploadState("done");
      router.push("/results");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
      setUploadState("error");
    }
  };

  return (
    <main className="page-wrapper">
      <header className="header-section">
        <h1 className="brand-title">Mbiu</h1>
        <p className="brand-tagline">
          Understand a music contract before you sign it.
        </p>
      </header>

      <form onSubmit={handleUpload} aria-label="Upload music contract for evaluation">
        <PrivacyNotice
          consentChecked={consentChecked}
          onConsentChange={setConsentChecked}
        />

        <FileDropzone
          selectedFile={selectedFile}
          onFileSelect={handleFileSelect}
          onError={setErrorMessage}
          disabled={uploadState === "uploading"}
        />

        <div className="turnstile-wrapper">
          <Turnstile
            onSuccess={(token) => setTurnstileToken(token)}
            onError={() => {
              setErrorMessage("Bot verification failed. Please refresh the page.");
            }}
            onExpire={() => setTurnstileToken(null)}
          />
        </div>

        {errorMessage && (
          <div className="status-alert error" role="alert" data-testid="upload-error-alert">
            <strong>Error: </strong>
            {errorMessage}
          </div>
        )}

        {statusMessage && uploadState === "done" && (
          <div className="status-alert success" role="status" data-testid="upload-success-alert">
            {statusMessage}
          </div>
        )}

        <div className="action-section">
          <button
            type="submit"
            className="submit-btn"
            disabled={!isSubmitEnabled}
            data-testid="submit-contract-btn"
          >
            {uploadState === "uploading" && <span className="spinner" aria-hidden="true" />}
            {uploadState === "uploading"
              ? "Uploading contract…"
              : "Check my contract"}
          </button>
        </div>

        <div className="demo-link-row" style={{ marginTop: "1.5rem", textAlign: "center" }}>
          <Link href="/results" className="text-toggle-btn" data-testid="link-to-results">
            View Live Results Page Demo →
          </Link>
        </div>
      </form>
    </main>
  );
}
