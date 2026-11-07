"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { AlertCircle, CheckCircle, Send } from "lucide-react";

export default function ReportPage() {
  const [submitted, setSubmitted] = useState(false);
  const [clauseTopic, setClauseTopic] = useState("");
  const [errorType, setErrorType] = useState("translation");
  const [details, setDetails] = useState("");
  const [contact, setContact] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[800px] px-4 py-10 sm:px-8 sm:py-16">
        <div className="rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <AlertCircle className="h-3.5 w-3.5" />
              Quality &amp; Accuracy
            </span>
          </div>

          <h1 className="mt-4 font-serif text-[2.2rem] font-semibold tracking-[-0.03em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2.8rem]">
            Report Incorrect Information
          </h1>

          <p className="mt-3 text-[1rem] leading-relaxed text-mbiu-ink-muted dark:text-[#c2c9cd]">
            Help us maintain high accuracy. Tell us about clause misclassifications or wording errors.
          </p>

          {submitted ? (
            <div className="mt-8 rounded-2xl border border-green-500/30 bg-green-500/10 p-6 text-center dark:bg-green-500/15">
              <CheckCircle className="mx-auto h-12 w-12 text-green-600 dark:text-green-400" />
              <h2 className="mt-3 font-serif text-[1.4rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                Report Received
              </h2>
              <p className="mt-2 text-[0.95rem] text-mbiu-ink/80 dark:text-[#c2c9cd]">
                Thank you for your feedback. Our team will review your correction shortly.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSubmitted(false);
                  setClauseTopic("");
                  setDetails("");
                  setContact("");
                }}
                className="mt-6 inline-flex items-center justify-center rounded-full bg-mbiu-indigo px-6 py-2.5 text-[0.9rem] font-semibold text-white shadow-sm transition hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
              >
                Submit another report
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-8 space-y-6">
              <div>
                <label className="block text-[0.9rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                  Clause Topic or Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Post-term Exclusivity, Master Rights, Royalties"
                  value={clauseTopic}
                  onChange={(e) => setClauseTopic(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-mbiu-ink/15 bg-white/80 px-4 py-2.5 text-[0.95rem] text-mbiu-ink outline-none transition focus:border-mbiu-indigo focus:ring-2 focus:ring-mbiu-indigo/20 dark:border-white/15 dark:bg-white/[0.06] dark:text-[#F6F2E9]"
                />
              </div>

              <div>
                <label className="block text-[0.9rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                  Type of Inaccuracy
                </label>
                <select
                  value={errorType}
                  onChange={(e) => setErrorType(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-mbiu-ink/15 bg-white/80 px-4 py-2.5 text-[0.95rem] text-mbiu-ink outline-none transition focus:border-mbiu-indigo focus:ring-2 focus:ring-mbiu-indigo/20 dark:border-white/15 dark:bg-white/[0.06] dark:text-[#F6F2E9]"
                >
                  <option value="translation">Summary wording or plain language error</option>
                  <option value="risk">Incorrect risk level or impact label</option>
                  <option value="recommendation">Question suggestion needs improvement</option>
                  <option value="other">Other issue</option>
                </select>
              </div>

              <div>
                <label className="block text-[0.9rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                  Description of the Issue
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe what was inaccurate and why."
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-mbiu-ink/15 bg-white/80 px-4 py-2.5 text-[0.95rem] text-mbiu-ink outline-none transition focus:border-mbiu-indigo focus:ring-2 focus:ring-mbiu-indigo/20 dark:border-white/15 dark:bg-white/[0.06] dark:text-[#F6F2E9]"
                />
              </div>

              <div>
                <label className="block text-[0.9rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9]">
                  Your Email or Phone (Optional)
                </label>
                <input
                  type="text"
                  placeholder="artist@example.com"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-mbiu-ink/15 bg-white/80 px-4 py-2.5 text-[0.95rem] text-mbiu-ink outline-none transition focus:border-mbiu-indigo focus:ring-2 focus:ring-mbiu-indigo/20 dark:border-white/15 dark:bg-white/[0.06] dark:text-[#F6F2E9]"
                />
              </div>

              <button
                type="submit"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-mbiu-indigo px-7 py-3 text-[0.95rem] font-semibold text-white shadow-md transition hover:bg-mbiu-indigo-hover dark:bg-mbiu-indigo-dark"
              >
                Submit Report
                <Send className="h-4 w-4" />
              </button>
            </form>
          )}
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
