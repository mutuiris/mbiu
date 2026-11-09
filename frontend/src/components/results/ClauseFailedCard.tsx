import React from "react";

import type { ClauseFailure } from "@/lib/api/generated/types.gen";
import { readableClauseName } from "@/lib/report";

import { Button } from "./ui";

interface ClauseFailedCardProps {
  failure: ClauseFailure;
  clauseNumber?: string | null;
  clauseHeading?: string | null;
  onRetry?: (clauseId: string) => void;
  isRetrying?: boolean;
}

/** A clause Mbiu tried to check but could not, because of an error. */
export const ClauseFailedCard: React.FC<ClauseFailedCardProps> = ({
  failure,
  clauseNumber,
  clauseHeading,
  onRetry,
  isRetrying = false,
}) => (
  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1" data-testid={`failed-${failure.clause_id}`}>
    <div className="min-w-0">
      <p className="break-words text-[0.92rem] font-semibold text-mbiu-ink dark:text-[#F4EFE6]">
        {readableClauseName({ number: clauseNumber, heading: clauseHeading })}
      </p>
      <p className="text-[0.85rem] text-mbiu-ink/65 dark:text-[#b9c1c5]">Mbiu couldn&apos;t check this clause. Try again.</p>
    </div>
    {failure.retryable && onRetry && (
      <Button disabled={isRetrying} onClick={() => onRetry(failure.clause_id)}>
        {isRetrying ? "Trying again…" : "Try again"}
      </Button>
    )}
  </div>
);
