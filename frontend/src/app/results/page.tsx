"use client";

import React, { useState } from "react";
import Link from "next/link";
import { LiveResults } from "@/components/results/LiveResults";
import { createSyntheticEventStream } from "@/lib/api/syntheticStream";
import type { EvaluationEvent } from "@/lib/api/stream";

export default function ResultsPage() {
  const [stream, setStream] = useState<AsyncGenerator<EvaluationEvent, void, unknown> | null>(null);

  const startSyntheticDemo = () => setStream(createSyntheticEventStream(350));

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

      {!stream ? (
        <section className="starter-panel" aria-label="Start evaluation options">
          <div className="starter-card demo-card">
            <h3>Try with Synthetic Contract</h3>
            <p>
              Experience the live NDJSON streaming pipeline immediately with pre-recorded Kenyan music agreement clauses.
            </p>
            <button type="button" className="start-demo-btn" onClick={startSyntheticDemo}>
              Start Live Stream Preview
            </button>
          </div>
        </section>
      ) : (
        <div className="stream-viewport">
          <div className="stream-controls">
            <button type="button" className="secondary-btn restart-btn" onClick={startSyntheticDemo}>
              Restart Stream
            </button>
          </div>
          <LiveResults eventStream={stream} onRetryAll={startSyntheticDemo} />
        </div>
      )}
    </main>
  );
}
