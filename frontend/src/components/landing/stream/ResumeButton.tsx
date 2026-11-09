import React from "react";
import type { Clause } from "@/lib/api/generated/types.gen";

export interface ResumeButtonProps {
  unfinished: Clause[];
  onClick: () => void;
  className?: string;
}

export function ResumeButton({
  unfinished,
  onClick,
  className = "",
}: ResumeButtonProps) {
  if (unfinished.length === 0) return null;

  return (
    <button type="button" className={`secondary-btn ${className}`} onClick={onClick}>
      Check the {unfinished.length === 1 ? "unfinished clause" : `${unfinished.length} unfinished clauses`}
    </button>
  );
}
