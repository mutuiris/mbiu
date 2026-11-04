"use client";

import React from "react";
import { AlertTriangle, HelpCircle } from "lucide-react";

export interface ClauseData {
  clauseId: string;
  page: number;
  title: string;
  badge: string;
  text: string;
  question: string;
}

interface ClauseCardProps {
  clause: ClauseData;
  isActive: boolean;
  onClick: () => void;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({ clause, isActive, onClick }) => {
  return (
    <div
      onClick={onClick}
      className={`cursor-pointer rounded-2xl p-6 transition-all duration-200 border ${
        isActive
          ? "bg-white border-[#EE6C4D] shadow-xl shadow-[#EE6C4D]/10 ring-2 ring-[#EE6C4D]/20"
          : "bg-white/80 border-[#E5E0D5] hover:border-[#CBD3D6] hover:bg-white shadow-sm"
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2.5 h-2.5 rotate-45 bg-[#EE6C4D] inline-block" />
        <span className="text-xs font-semibold uppercase tracking-wider text-[#5C666B]">
          {clause.title}
        </span>
      </div>

      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FCEAE6] text-[#D95338] text-xs font-medium mb-3">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>{clause.badge}</span>
      </div>

      <p className="text-sm font-medium text-[#1A252C] leading-relaxed mb-4 italic">
        {clause.text}
      </p>

      <div className="pt-3 border-t border-[#F0ECE1] flex items-start gap-2 text-xs text-[#5C666B]">
        <HelpCircle className="w-4 h-4 text-[#005C66] shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-[#1A252C]">Ask them: </span>
          <span>{clause.question}</span>
        </div>
      </div>
    </div>
  );
};
