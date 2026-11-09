import React from "react";
import { Turnstile } from "@/components/Turnstile";
import type { Clause } from "@/lib/api/generated/types.gen";

export interface ResumePanelProps {
  resultsStatus: string | null;
  isStreaming: boolean;
  clausesToCheck: Clause[] | null;
  turnstileKey: number;
  onCheckClauses: (token: string) => void;
  onSecurityCheckError: () => void;
  className?: string;
}

export function ResumePanel({
  resultsStatus,
  isStreaming,
  clausesToCheck,
  turnstileKey,
  onCheckClauses,
  onSecurityCheckError,
  className = "",
}: ResumePanelProps) {
  return (
    <div className={`resume-panel ${className}`} role="status" aria-live="polite">
      {resultsStatus && <p>{resultsStatus}</p>}
      {!isStreaming && clausesToCheck && (
        <>
          <p>
            Checking {clausesToCheck.length === 1 ? "1 clause" : `${clausesToCheck.length} clauses`}{" "}
            again after a quick security check.
          </p>
          <Turnstile
            key={turnstileKey}
            onSuccess={onCheckClauses}
            onError={onSecurityCheckError}
          />
        </>
      )}
    </div>
  );
}
