/**
 * Client-side file validation rules for Mbiu uploads.
 * Matches backend MB-02 limits: max 10 MB, text-based PDF format.
 */

export const MAX_UPLOAD_MB = 10;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

export type ValidationErrorCode =
  | "NO_FILE"
  | "EMPTY_FILE"
  | "INVALID_TYPE"
  | "FILE_TOO_LARGE";

export type ValidationResult =
  | { valid: true; file: File }
  | { valid: false; error: string; code: ValidationErrorCode };

/**
 * Validates a user-selected file before sending it over the network.
 */
export function validateContractFile(file?: File | null): ValidationResult {
  if (!file) {
    return {
      valid: false,
      code: "NO_FILE",
      error: "Please select a PDF contract to evaluate.",
    };
  }

  if (file.size === 0) {
    return {
      valid: false,
      code: "EMPTY_FILE",
      error: "This file appears to be empty. Please upload a valid PDF contract.",
    };
  }

  // Check file extension and MIME type
  const isPdfExtension = file.name.toLowerCase().endsWith(".pdf");
  const isPdfMime = file.type === "application/pdf" || file.type === "";

  if (!isPdfExtension || (!isPdfMime && file.type !== "")) {
    return {
      valid: false,
      code: "INVALID_TYPE",
      error:
        "Only text-based PDF documents are supported. Scans, DOCX, and image files are not supported in this version.",
    };
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      valid: false,
      code: "FILE_TOO_LARGE",
      error: `This file is larger than Mbiu can check right now (limit: ${MAX_UPLOAD_MB} MB). Please upload a smaller file.`,
    };
  }

  return { valid: true, file };
}

/**
 * Formats bytes into a human-readable size string (e.g. "1.4 MB").
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
