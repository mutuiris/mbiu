import React from "react";

import type { Summary } from "@/lib/api/generated/types.gen";

import { ReportCard } from "./ui";

interface SummaryCardProps {
  summary: Summary;
}

/** What the report adds after the clause cards. Questions to ask sit at the top instead. */
export const SummaryCard: React.FC<SummaryCardProps> = ({ summary }) => {
  const missing = summary.missing_protections;
  const goodNews = summary.good_news ?? [];
  if (missing.length === 0 && goodNews.length === 0) return null;

  return (
    <ReportCard aria-labelledby="summary-extra-title">
      <h2
        id="summary-extra-title"
        className="font-serif text-[1.3rem] font-medium leading-tight text-mbiu-ink dark:text-[#F6F2E9]"
      >
        More from your report
      </h2>

      {missing.length > 0 && (
        <div className="mt-4">
          <h3 className="text-[0.95rem] font-bold text-mbiu-ink dark:text-[#F4EFE6]">Missing from your contract</h3>
          <p className="mt-1 text-[0.88rem] text-mbiu-ink/65 dark:text-[#b9c1c5]">
            Usual contracts protect you here. Yours says nothing about it.
          </p>
          <ul className="mt-2">
            {missing.map((item) => (
              <li key={item.template_id} className="border-t border-[#e9dec9] py-2.5 dark:border-white/10">
                <p className="text-[0.95rem] font-semibold text-mbiu-ink dark:text-[#F4EFE6]">{item.title}</p>
                <p className="mt-0.5 text-[0.92rem] text-mbiu-ink/80 dark:text-[#d6dadc]">Ask them: {item.ask_them}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {goodNews.length > 0 && (
        <div className="mt-4">
          <h3 className="text-[0.95rem] font-bold text-mbiu-ink dark:text-[#F4EFE6]">Good news</h3>
          <ul className="mt-2">
            {goodNews.map((note) => (
              <li
                key={`${note.clause_id}-${note.text}`}
                className="flex gap-2 border-t border-[#e9dec9] py-2.5 text-[0.95rem] text-mbiu-ink dark:border-white/10 dark:text-[#F4EFE6]"
              >
                <span aria-hidden="true" className="text-[#0f6867] dark:text-[#8fdad7]">
                  ✓
                </span>
                <span>{note.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ReportCard>
  );
};
