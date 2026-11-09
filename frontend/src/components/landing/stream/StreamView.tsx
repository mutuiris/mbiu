import React from "react";
import { Footer } from "@/components/footer/Footer";
import { Navbar } from "@/components/Navbar";
import { KeepResultsSwitch } from "@/components/results/KeepResultsSwitch";
import { LiveResults } from "@/components/results/LiveResults";
import { SiteBackdrop } from "@/components/SiteBackdrop";
import { ResumeButton } from "./ResumeButton";
import { ResumePanel } from "./ResumePanel";
import { StreamControls } from "./StreamControls";
import type { Clause } from "@/lib/api/generated/types.gen";
import type { EvaluationEvent } from "@/lib/api/stream";

type EventStream = AsyncGenerator<EvaluationEvent, void, unknown>;

export interface StreamViewProps {
  stream: EventStream;
  selectedFile: File | null;
  isStreaming: boolean;
  keptSince: number | null;
  clausesToCheck: Clause[] | null;
  unfinished: Clause[];
  resultsStatus: string | null;
  turnstileKey: number;
  onKeepChange: (keep: boolean) => void;
  onStartOver: () => void;
  onCheckClauses: (token: string) => void;
  onCheckUnfinished: () => void;
  onRetryClause?: (clauseId: string) => void;
  onSecurityCheckError: () => void;
}

export function StreamView({
  stream,
  selectedFile,
  isStreaming,
  keptSince,
  clausesToCheck,
  unfinished,
  resultsStatus,
  turnstileKey,
  onKeepChange,
  onStartOver,
  onCheckClauses,
  onCheckUnfinished,
  onRetryClause,
  onSecurityCheckError,
}: StreamViewProps) {
  const isIdle = !isStreaming && !clausesToCheck;

  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <SiteBackdrop variant="results" />
      <Navbar basePath="/" />

      <main className="results-page relative z-10 mx-auto w-full max-w-[880px] px-5 pb-20 pt-8 sm:px-8">
        <StreamControls onStartOver={onStartOver} />

        <KeepResultsSwitch kept={keptSince !== null} onChange={onKeepChange} />

        <ResumePanel
          resultsStatus={resultsStatus}
          isStreaming={isStreaming}
          clausesToCheck={clausesToCheck}
          turnstileKey={turnstileKey}
          onCheckClauses={onCheckClauses}
          onSecurityCheckError={onSecurityCheckError}
        />

        {isIdle && (
          <ResumeButton unfinished={unfinished} onClick={onCheckUnfinished} />
        )}

        <LiveResults
          eventStream={stream}
          onRetryAll={onStartOver}
          onRetryClause={isIdle ? onRetryClause : undefined}
          file={selectedFile}
        />
      </main>

      <Footer basePath="/" />
    </div>
  );
}
