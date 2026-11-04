"use client";

import React, { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

// Ensure worker is configured safely
if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

export interface ClauseLocation {
  clauseId: string;
  page: number;
}

export interface PdfViewerProps {
  fileUrl: File | ArrayBuffer | string | null;
  activeClause?: ClauseLocation | null;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({ fileUrl, activeClause }) => {
  const [numPages, setNumPages] = useState<number>(0);

  useEffect(() => {
    if (activeClause?.page) {
      const pageEl = document.getElementById(`pdf-page-${activeClause.page}`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeClause]);

  if (!fileUrl) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-[#E5E0D5] rounded-2xl p-8 text-center bg-[#F7F5EF]/30">
        <h3 className="font-serif text-lg font-bold text-[#1A252C] mb-1">No contract loaded</h3>
        <p className="text-xs text-[#5C666B]">Upload a PDF to view highlighted clauses</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto max-h-[750px] p-4 flex flex-col items-center gap-6 bg-[#E8E3D8]/40 rounded-2xl">
      <Document
        file={fileUrl}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
        loading={
          <div className="py-12 text-sm text-[#5C666B]">Loading PDF Document...</div>
        }
      >
        {Array.from(new Array(numPages), (_, index) => {
          const pageNum = index + 1;
          const isActive = activeClause?.page === pageNum;

          return (
            <div
              key={`page_${pageNum}`}
              id={`pdf-page-${pageNum}`}
              className={`transition-all duration-300 rounded-lg overflow-hidden shadow-md ${
                isActive ? "ring-4 ring-[#EE6C4D] shadow-xl scale-[1.01]" : ""
              }`}
            >
              <Page pageNumber={pageNum} renderTextLayer={false} renderAnnotationLayer={false} />
            </div>
          );
        })}
      </Document>
    </div>
  );
};
