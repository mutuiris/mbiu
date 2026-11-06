"use client";

import React, { useCallback } from "react";
import { FileRejection, useDropzone } from "react-dropzone";

import {
  formatFileSize,
  MAX_UPLOAD_BYTES,
  MAX_UPLOAD_MB,
  validateContractFile,
} from "@/lib/validation";

interface FileDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onError: (errorMsg: string | null) => void;
  disabled?: boolean;
}

export function FileDropzone({
  selectedFile,
  onFileSelect,
  onError,
  disabled = false,
}: FileDropzoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[], rejections: FileRejection[]) => {
      onError(null);

      if (rejections.length > 0) {
        const rejection = rejections[0];
        const hasSizeError = rejection.errors.some((e) => e.code === "file-too-large");
        const hasTypeError = rejection.errors.some((e) => e.code === "file-invalid-type");

        if (hasSizeError) {
          onError(`This file is larger than Mbiu can check right now (limit: ${MAX_UPLOAD_MB} MB).`);
        } else if (hasTypeError) {
          onError("Only text-based PDF files are supported. Please select a .pdf document.");
        } else {
          onError(rejection.errors[0]?.message || "Could not accept this file.");
        }
        return;
      }

      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      const validation = validateContractFile(file);
      if (!validation.valid) {
        onError(validation.error);
        return;
      }

      onFileSelect(validation.file);
    },
    [onFileSelect, onError]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    maxSize: MAX_UPLOAD_BYTES,
    disabled,
  });

  return (
    <div className="dropzone-wrapper">
      <div
        {...getRootProps()}
        className={`dropzone-area ${isDragActive ? "drag-active" : ""} ${
          isDragReject ? "drag-reject" : ""
        } ${disabled ? "disabled" : ""} ${selectedFile ? "has-file" : ""}`}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label="Upload contract PDF"
      >
        <input {...getInputProps()} aria-label="Choose PDF contract file" />

        <div className="dropzone-content">
          <svg
            className="dropzone-icon"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <polyline points="9 15 12 12 15 15" />
          </svg>

          {selectedFile ? (
            <div className="selected-file-info">
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">({formatFileSize(selectedFile.size)})</span>
              <p className="file-change-hint">Tap or drop another file to replace</p>
            </div>
          ) : (
            <div className="empty-dropzone-prompt">
              <p className="prompt-primary">
                <strong>Drop your contract PDF here</strong>, or{" "}
                <span className="browse-link">browse files</span>
              </p>
              <p className="prompt-secondary">
                Text-based PDF only • Maximum {MAX_UPLOAD_MB} MB • Tested up to 40 pages
              </p>
            </div>
          )}
        </div>
      </div>

      {selectedFile && (
        <div className="clear-file-action">
          <button
            type="button"
            className="clear-file-btn"
            onClick={(e) => {
              e.stopPropagation();
              onFileSelect(null);
              onError(null);
            }}
            disabled={disabled}
          >
            Remove file
          </button>
        </div>
      )}
    </div>
  );
}
