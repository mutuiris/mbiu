"use client";

import React, { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export interface ClauseLocation {
  clauseId: string;
  page: number;
  startOffset?: number;
  endOffset?: number;
  text?: string;
}

interface PdfViewerProps {
  fileUrl?: string | ArrayBuffer | File | null;
  activeClause?: ClauseLocation | null;
  clauses?: ClauseLocation[];
  onClauseSelect?: (clauseId: string) => void;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({
  fileUrl,
  activeClause,
  clauses = [],
  onClauseSelect,
}) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  // Auto-scroll to page when active clause changes
  useEffect(() => {
    if (activeClause?.page) {
      const pageElement = document.getElementById(`pdf-page-${activeClause.page}`);
      if (pageElement) {
        pageElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeClause]);

  return (
    <div 
      ref={containerRef}
      className="flex flex-col items-center w-full max-w-4xl mx-auto p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border h-[80vh] overflow-y-auto"
    >
      {fileUrl ? (
        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<div className="p-8 text-gray-500 animate-pulse">Loading contract PDF...</div>}
          error={<div className="p-8 text-red-500 font-medium">Unable to display PDF preview.</div>}
        >
          {Array.from(new Array(numPages || 0), (_, index) => {
            const pageNum = index + 1;
            const isCurrentPage = activeClause?.page === pageNum;

            return (
              <div
                key={`page_${pageNum}`}
                id={`pdf-page-${pageNum}`}
                className={`mb-6 shadow-md border rounded relative transition-all duration-300 ${
                  isCurrentPage ? "ring-4 ring-amber-500/50 border-amber-500" : "border-gray-200"
                }`}
              >
                <Page
                  pageNumber={pageNum}
                  renderTextLayer={true}
                  renderAnnotationLayer={false}
                  width={Math.min(typeof window !== "undefined" ? window.innerWidth - 64 : 600, 680)}
                />
              </div>
            );
          })}
        </Document>
      ) : (
        <div className="flex flex-col items-center justify-center h-full p-12 text-center text-gray-400">
          <p className="text-lg font-medium">No contract loaded</p>
          <p className="text-sm mt-1">Upload a PDF to view highlighted clauses</p>
        </div>
      )}
    </div>
  );
};
