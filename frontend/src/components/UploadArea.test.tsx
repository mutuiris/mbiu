import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { UploadArea } from "./UploadArea";

describe("UploadArea Component", () => {
  const defaultProps = {
    selectedFile: null,
    consentChecked: false,
    turnstileKey: 0,
    isUploading: false,
    isSubmitEnabled: false,
    errorMessage: null,
    notice: null,
    onFileSelect: vi.fn(),
    onConsentChange: vi.fn(),
    onTurnstileSuccess: vi.fn(),
    onTurnstileError: vi.fn(),
    onTurnstileExpire: vi.fn(),
    onUpload: vi.fn(),
    onError: vi.fn(),
  };

  it("renders upload heading and description", () => {
    const markup = renderToStaticMarkup(<UploadArea {...defaultProps} />);
    expect(markup).toContain("Upload your contract");
    expect(markup).toContain("We read it once, explain each clause");
  });

  it("renders disabled submit button when submission is not enabled", () => {
    const markup = renderToStaticMarkup(<UploadArea {...defaultProps} isSubmitEnabled={false} />);
    expect(markup).toContain("disabled");
    expect(markup).toContain("Check my contract");
  });

  it("renders loading state when isUploading is true", () => {
    const markup = renderToStaticMarkup(
      <UploadArea {...defaultProps} isUploading={true} isSubmitEnabled={true} />
    );
    expect(markup).toContain("Uploading contract…");
    expect(markup).toContain("spinner");
  });

  it("renders notice alert when notice is provided", () => {
    const markup = renderToStaticMarkup(
      <UploadArea {...defaultProps} notice="Results are kept for 1 hour." />
    );
    expect(markup).toContain("Results are kept for 1 hour.");
    expect(markup).toContain("status-alert info");
  });

  it("renders error message alert when errorMessage is provided", () => {
    const markup = renderToStaticMarkup(
      <UploadArea {...defaultProps} errorMessage="File too large." />
    );
    expect(markup).toContain("File too large.");
    expect(markup).toContain("status-alert error");
  });
});
