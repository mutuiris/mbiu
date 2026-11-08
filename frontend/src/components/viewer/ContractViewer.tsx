"use client";

// Must load before pdf.js
import "@/lib/browser-polyfills";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";

import { escapeHtml, highlightedItems, pagePosition } from "@/lib/highlight";

// Bundled with the app, so the browser never fetches pdf.js code from a third party.
// The legacy worker carries its own polyfills for browsers without the newest JavaScript.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/legacy/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

// Pages stay placeholders until they come within this distance of the visible area
const PRELOAD_MARGIN = "800px 0px";
const A4_RATIO = 1.414;

export interface ViewerClause {
  clauseId: string;
  pages: number[];
  text: string;
}

export interface ContractViewerProps {
  /** The artist's own file, read in the browser. It is never uploaded again or stored. */
  file: File;
  clause: ViewerClause | null;
  /** On phones the viewer is a full-screen sheet, shown only while open. */
  isOpen: boolean;
  onClose: () => void;
}

export default function ContractViewer({ file, clause, isOpen, onClose }: ContractViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [numPages, setNumPages] = useState(0);
  const [width, setWidth] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!clause) return;
    const firstPage = Math.min(...clause.pages);
    scrollRef.current
      ?.querySelector(`#viewer-page-${firstPage}`)
      ?.scrollIntoView({ block: "start" });
  }, [clause]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  return (
    <aside
      className={`contract-viewer${isOpen ? " is-open" : ""}`}
      aria-label="Your contract"
    >
      <div className="contract-viewer-bar">
        <button
          type="button"
          className="secondary-btn contract-viewer-close"
          onClick={onClose}
          aria-label="Back to evaluation results"
        >
          ← Back to evaluation
        </button>
        <span className="contract-viewer-title">Your contract</span>
      </div>
      <div className="contract-viewer-scroll" ref={scrollRef}>
        {loadFailed ? (
          <p className="contract-viewer-message" role="alert">
            This PDF could not be shown here. Your results are not affected.
          </p>
        ) : (
          <Document
            file={file}
            onLoadSuccess={({ numPages: pages }) => setNumPages(pages)}
            onLoadError={() => setLoadFailed(true)}
            loading={<p className="contract-viewer-message">Opening your contract…</p>}
          >
            {width > 0 &&
              Array.from({ length: numPages }, (_, index) => (
                <LazyPage
                  key={index + 1}
                  pageNumber={index + 1}
                  width={width}
                  clause={clause}
                  root={scrollRef}
                />
              ))}
          </Document>
        )}
      </div>
    </aside>
  );
}

interface LazyPageProps {
  pageNumber: number;
  width: number;
  clause: ViewerClause | null;
  root: React.RefObject<HTMLDivElement | null>;
}

function LazyPage({ pageNumber, width, clause, root }: LazyPageProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [nearView, setNearView] = useState(false);
  const [items, setItems] = useState<string[]>([]);

  const position = clause ? pagePosition(pageNumber, clause.pages) : null;
  // A page holding the selected clause renders straight away so the jump lands on it
  const shown = nearView || position !== null;

  useEffect(() => {
    const element = ref.current;
    if (!element || nearView) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setNearView(true);
          observer.disconnect();
        }
      },
      { root: root.current, rootMargin: PRELOAD_MARGIN },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [nearView, root]);

  const marked = useMemo(
    () => (clause && position ? highlightedItems(items, clause.text, position) : new Set<number>()),
    [clause, position, items],
  );

  const renderText = useCallback(
    ({ str, itemIndex }: { str: string; itemIndex: number }) =>
      marked.has(itemIndex) ? `<mark class="clause-highlight">${escapeHtml(str)}</mark>` : escapeHtml(str),
    [marked],
  );

  const scrollToHighlight = useCallback(() => {
    if (position !== "only" && position !== "first") return;
    ref.current?.querySelector(".clause-highlight")?.scrollIntoView({ block: "center" });
  }, [position]);

  return (
    <div
      ref={ref}
      id={`viewer-page-${pageNumber}`}
      className={`contract-viewer-page${position ? " has-clause" : ""}`}
      style={shown ? undefined : { height: Math.round(width * A4_RATIO) }}
      aria-label={`Page ${pageNumber}`}
    >
      {shown && (
        <Page
          pageNumber={pageNumber}
          width={width}
          renderAnnotationLayer={false}
          customTextRenderer={renderText}
          onGetTextSuccess={({ items: textItems }) =>
            setItems(textItems.map((item) => ("str" in item ? item.str : "")))
          }
          onRenderTextLayerSuccess={scrollToHighlight}
        />
      )}
    </div>
  );
}
