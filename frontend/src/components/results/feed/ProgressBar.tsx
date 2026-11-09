import React from "react";
import type { Progress } from "@/lib/api/generated/types.gen";

export interface ProgressBarProps {
  progress: Progress | null;
  isStreaming: boolean;
  totalClauses?: number;
  evaluatedCount?: number;
}

const STAGE_LABELS: Record<string, string> = {
  extract: "Extracting contract text…",
  segment: "Splitting into clauses…",
  map: "Mapping cross-references…",
  retrieve: "Finding reviewed standards…",
  compare: "Comparing against standard…",
  verify: "Verifying exact quotes…",
  summarise: "Compiling final summary…",
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  isStreaming,
  totalClauses = 0,
  evaluatedCount = 0,
}) => {
  if (!isStreaming && !progress) return null;

  const total = progress?.total || totalClauses || 1;
  const current = progress?.done ?? evaluatedCount;
  const percentage = Math.min(100, Math.round((current / total) * 100));
  const stageName = progress?.stage ? STAGE_LABELS[progress.stage] || progress.stage : "Checking contract…";

  return (
    <div className="progress-container" role="region" aria-label="Evaluation Progress">
      <div className="progress-header">
        <span className="progress-stage">
          {isStreaming && <span className="progress-pulse" />}
          {isStreaming ? stageName : "Analysis Complete"}
        </span>
        <span className="progress-stats" aria-live="polite">
          {current} of {total} clauses checked ({percentage}%)
        </span>
      </div>
      <div className="progress-track" aria-hidden="true">
        <div
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
