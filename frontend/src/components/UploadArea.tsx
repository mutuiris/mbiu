import React from "react";
import { FileDropzone } from "@/components/FileDropzone";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { Turnstile } from "@/components/Turnstile";

export interface UploadAreaProps {
  selectedFile: File | null;
  consentChecked: boolean;
  turnstileKey: number;
  isUploading: boolean;
  isSubmitEnabled: boolean;
  errorMessage: string | null;
  notice: string | null;
  onFileSelect: (file: File | null) => void;
  onConsentChange: (checked: boolean) => void;
  onTurnstileSuccess: (token: string) => void;
  onTurnstileError: () => void;
  onTurnstileExpire: () => void;
  onUpload: (e: React.FormEvent) => void;
  onError: (msg: string | null) => void;
  className?: string;
}

export function UploadArea({
  selectedFile,
  consentChecked,
  turnstileKey,
  isUploading,
  isSubmitEnabled,
  errorMessage,
  notice,
  onFileSelect,
  onConsentChange,
  onTurnstileSuccess,
  onTurnstileError,
  onTurnstileExpire,
  onUpload,
  onError,
  className = "",
}: UploadAreaProps) {
  return (
    <div id="upload" className={`mx-auto w-full max-w-[880px] scroll-mt-28 ${className}`}>
      <h3 className="font-serif text-[1.65rem] font-semibold tracking-[-0.02em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2rem]">
        Upload your contract
      </h3>
      <p className="mt-2 text-[0.92rem] text-mbiu-ink/70 dark:text-[#B9C1C5] sm:text-[0.95rem]">
        We read it once, explain each clause, and give you the questions to ask.
      </p>

      {notice && (
        <div className="status-alert info mt-6" role="status">
          {notice}
        </div>
      )}

      <form onSubmit={onUpload} className="mt-6">
        <div id="privacy" className="scroll-mt-28">
          <PrivacyNotice consentChecked={consentChecked} onConsentChange={onConsentChange} />
        </div>

        <FileDropzone
          selectedFile={selectedFile}
          onFileSelect={onFileSelect}
          onError={onError}
          disabled={isUploading}
        />

        <div className="turnstile-wrapper">
          <Turnstile
            key={turnstileKey}
            onSuccess={onTurnstileSuccess}
            onError={onTurnstileError}
            onExpire={onTurnstileExpire}
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
    </div>
  );
}
