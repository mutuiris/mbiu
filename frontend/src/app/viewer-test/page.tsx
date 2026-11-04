"use client";

import React, { useState } from "react";
import { PdfViewer, ClauseLocation } from "@/components/PdfViewer";
import { Header } from "@/components/layout/Header";
import { ClauseCard, ClauseData } from "@/components/viewer/ClauseCard";

const MOCK_CLAUSES: ClauseData[] = [
  {
    clauseId: "c1",
    page: 1,
    title: "Clause 7.2 — Post-term exclusivity",
    badge: "Worth asking about",
    text: "“Your agreement could restrict you from working with other labels for two years after it ends.”",
    question: "“What happens if another label approaches me during this period?”",
  },
  {
    clauseId: "c2",
    page: 2,
    title: "Clause 12.1 — Royalty Deduction",
    badge: "Needs review",
    text: "“8% of net receipts, after all recording and marketing costs are recouped.”",
    question: "“Can recording costs be recouped only from royalties?”",
  },
];

export default function ViewerTestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [activeClause, setActiveClause] = useState<ClauseLocation | null>(null);

  return (
    <div className="min-h-screen bg-[#F7F5EF] text-[#1A252C] font-sans flex flex-col">
      <Header onFileSelect={setFile} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-8 grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Clause Sidebar */}
        <aside className="md:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-serif text-xl font-bold text-[#1A252C]">Detected Clauses</h2>
            <span className="text-xs text-[#5C666B] font-medium font-mono">
              {MOCK_CLAUSES.length} items
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {MOCK_CLAUSES.map((clause) => (
              <ClauseCard
                key={clause.clauseId}
                clause={clause}
                isActive={activeClause?.clauseId === clause.clauseId}
                onClick={() => setActiveClause(clause)}
              />
            ))}
          </div>
        </aside>

        {/* PDF Viewer Canvas Container */}
        <section className="md:col-span-7 bg-white/70 backdrop-blur-sm border border-[#E5E0D5] rounded-3xl p-6 shadow-sm min-h-[650px] flex flex-col">
          <PdfViewer fileUrl={file} activeClause={activeClause} />
        </section>
      </main>
    </div>
  );
}
