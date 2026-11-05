"use client";

import React, { useState } from "react";
import Link from "next/link";
import { LiveResults } from "@/components/results/LiveResults";
import { createSyntheticEventStream } from "@/lib/api/syntheticStream";
import { fetchEvaluationStream, type EvaluationEvent } from "@/lib/api/stream";

export default function ResultsPage() {
  const [stream, setStream] = useState<AsyncGenerator<EvaluationEvent, void, unknown> | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [turnstileToken, setTurnstileToken] = useState("synthetic-preview-token");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const startSyntheticDemo = () => {
    setSubmitError(null);
    setHasStarted(true);
    setStream(createSyntheticEventStream(350));
  };

  const handleLiveUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const evaluationStream = await fetchEvaluationStream({
        file: uploadFile,
        turnstileToken: turnstileToken || "dev-token",
      });
      setHasStarted(true);
      setStream(evaluationStream);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to connect to evaluation stream.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="page-wrapper results-page">
      <header className="results-header">
        <div className="header-nav">
          <Link href="/" className="back-link">
            ← Back to Home
          </Link>
          <span className="brand-badge">Mbiu Contract Checker</span>
        </div>
        <h1 className="results-title">Contract Evaluation Results</h1>
        <p className="results-description">
          Real-time clause analysis. Cards appear in order of importance to you as they finish checking.
        </p>
      </header>

      {!hasStarted ? (
        <section className="starter-panel" aria-label="Start evaluation options">
          <div className="starter-card demo-card">
            <h3>Try with Synthetic Contract</h3>
            <p>
              Experience the live NDJSON streaming pipeline immediately with pre-recorded Kenyan music agreement clauses.
            </p>
            <button
              type="button"
              className="start-demo-btn"
              onClick={startSyntheticDemo}
            >
              Start Live Stream Preview
            </button>
          </div>

          <div className="divider-or">OR</div>

          <div className="starter-card upload-card">
            <h3>Stream From a Local PDF</h3>
            <p>Connect directly to the live backend endpoint (`POST /api/v1/evaluations`).</p>
            <form onSubmit={handleLiveUpload} className="inline-upload-form">
              <input
                type="file"
                accept="application/pdf"
                className="file-input"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                required
              />
              <input
                type="hidden"
                value={turnstileToken}
                onChange={(e) => setTurnstileToken(e.target.value)}
              />
              {submitError && (
                <div className="status-alert error" role="alert">
                  {submitError}
                </div>
              )}
              <button
                type="submit"
                className="upload-submit-btn"
                disabled={!uploadFile || isSubmitting}
              >
                {isSubmitting ? "Connecting to stream…" : "Upload & Stream"}
              </button>
            </form>
          </div>
        </section>
      ) : (
        <div className="stream-viewport">
          <div className="stream-controls">
            <button
              type="button"
              className="secondary-btn restart-btn"
              onClick={startSyntheticDemo}
            >
              Restart Stream
            </button>
          </div>
          <LiveResults
            eventStream={stream}
            onRetryClause={(clauseId) => {
              // Simulated retry callback
              console.log("Retrying clause", clauseId);
            }}
            onRetryAll={startSyntheticDemo}
          />
        </div>
      )}
    </main>
  );
}
