import { describe, expect, it } from "vitest";

import {
  formatFileSize,
  MAX_UPLOAD_BYTES,
  MAX_UPLOAD_MB,
  validateContractFile,
} from "./validation";

function createMockFile(name: string, size: number, type = "application/pdf"): File {
  const buffer = new Uint8Array(size);
  return new File([buffer], name, { type });
}

describe("validateContractFile", () => {
  it("rejects null or undefined file", () => {
    const res = validateContractFile(null);
    expect(res.valid).toBe(false);
    if (!res.valid) {
      expect(res.code).toBe("NO_FILE");
      expect(res.error).toContain("Please select a PDF");
    }
  });

  it("rejects an empty file (0 bytes)", () => {
    const file = createMockFile("empty.pdf", 0);
    const res = validateContractFile(file);
    expect(res.valid).toBe(false);
    if (!res.valid) {
      expect(res.code).toBe("EMPTY_FILE");
      expect(res.error).toContain("empty");
    }
  });

  it("rejects non-PDF file extensions", () => {
    const wordFile = createMockFile("contract.docx", 1024, "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    const resWord = validateContractFile(wordFile);
    expect(resWord.valid).toBe(false);
    if (!resWord.valid) {
      expect(resWord.code).toBe("INVALID_TYPE");
    }

    const imageFile = createMockFile("scan.jpg", 1024, "image/jpeg");
    const resImage = validateContractFile(imageFile);
    expect(resImage.valid).toBe(false);
    if (!resImage.valid) {
      expect(resImage.code).toBe("INVALID_TYPE");
    }
  });

  it("rejects file exceeding MAX_UPLOAD_MB", () => {
    const oversized = createMockFile("huge.pdf", MAX_UPLOAD_BYTES + 1);
    const res = validateContractFile(oversized);
    expect(res.valid).toBe(false);
    if (!res.valid) {
      expect(res.code).toBe("FILE_TOO_LARGE");
      expect(res.error).toContain(`${MAX_UPLOAD_MB} MB`);
    }
  });

  it("accepts a valid PDF within size limit", () => {
    const validFile = createMockFile("recording_contract.pdf", 2 * 1024 * 1024);
    const res = validateContractFile(validFile);
    expect(res.valid).toBe(true);
    if (res.valid) {
      expect(res.file.name).toBe("recording_contract.pdf");
    }
  });

  it("accepts a PDF at exactly the size limit", () => {
    const limitFile = createMockFile("exact_limit.pdf", MAX_UPLOAD_BYTES);
    const res = validateContractFile(limitFile);
    expect(res.valid).toBe(true);
  });
});

describe("formatFileSize", () => {
  it("formats bytes, KB, and MB properly", () => {
    expect(formatFileSize(500)).toBe("500 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(3.5 * 1024 * 1024)).toBe("3.5 MB");
  });
});
