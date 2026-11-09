"use client";

import React, { useState } from "react";

export interface CopyButtonProps {
  text: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  label = "📋 Copy",
  copiedLabel = "✓ Copied!",
  className = "copy-btn",
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Clipboard fallback
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`${className} ${copied ? "copied" : ""}`}
      aria-label="Copy to clipboard"
    >
      {copied ? copiedLabel : label}
    </button>
  );
};
