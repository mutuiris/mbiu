"use client";

import React from "react";
import Link from "next/link";
import { FileUp } from "lucide-react";

interface HeaderProps {
  onFileSelect: (file: File | null) => void;
}

export const Header: React.FC<HeaderProps> = ({ onFileSelect }) => {
  return (
    <header className="px-8 py-5 border-b border-[#E5E0D5] bg-[#F7F5EF]/80 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Link href="/" className="font-serif text-2xl font-bold tracking-tight text-[#005C66]">
          mbiu
        </Link>
        <span className="text-xs px-2.5 py-1 rounded-full bg-[#E8E3D8] text-[#5C666B] font-medium font-mono">
          MB-22 PDF Viewer Sandbox
        </span>
      </div>

      <label className="flex items-center gap-2 bg-[#005C66] hover:bg-[#004A52] text-white font-medium px-5 py-2.5 rounded-full text-sm transition cursor-pointer shadow-md shadow-[#005C66]/10">
        <FileUp className="w-4 h-4" />
        <span>Upload contract PDF</span>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => onFileSelect(e.target.files?.[0] || null)}
          className="hidden"
        />
      </label>
    </header>
  );
};
