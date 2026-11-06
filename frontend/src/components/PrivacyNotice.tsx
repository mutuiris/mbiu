"use client";

import React, { useState } from "react";

interface PrivacyNoticeProps {
  consentChecked: boolean;
  onConsentChange: (checked: boolean) => void;
}

export function PrivacyNotice({
  consentChecked,
  onConsentChange,
}: PrivacyNoticeProps) {
  const [detailsExpanded, setDetailsExpanded] = useState(false);

  return (
    <section aria-labelledby="privacy-heading" className="privacy-card">
      <div className="disclaimer-banner" role="note">
        <strong>Important:</strong> Mbiu is an educational and evaluation tool.
        It is <em>not legal advice</em>, does not draft or negotiate contracts,
        and does not determine whether a clause is legally enforceable.
      </div>

      <h2 id="privacy-heading" className="privacy-title">
        How your contract is handled
      </h2>

      <p className="privacy-summary">
        We respect the privacy and commercial sensitivity of your music. Your
        contract is evaluated <strong>in memory</strong> and is{" "}
        <strong>never stored</strong> in any database, disk, or application log.
      </p>

      <button
        type="button"
        className="text-toggle-btn"
        aria-expanded={detailsExpanded}
        onClick={() => setDetailsExpanded((prev) => !prev)}
      >
        {detailsExpanded
          ? "Hide provider details"
          : "Read full privacy & data transfer details"}
      </button>

      {detailsExpanded && (
        <div className="privacy-details">
          <h3>Data handling & cross-border transfers</h3>
          <p>
            In compliance with Kenya&apos;s Data Protection Act, here is exactly
            where data goes:
          </p>
          <ul>
            <li>
              <strong>Google Gemini API (paid tier):</strong> receives clause
              text, linked clauses, template excerpts and follow-up questions,
              with storage turned off. It is not stored for Mbiu. Google keeps
              logs for a limited period for abuse monitoring and legal
              requirements.
            </li>
            <li>
              <strong>OpenAI API (failover only, off by default):</strong>{" "}
              receives the same, only when Gemini is unavailable, with storage
              turned off on every call.
            </li>
            <li>
              <strong>Services that never see contract text:</strong>
              <ul>
                <li>Supabase: public templates, statutes and guidance only.</li>
                <li>Vercel: serves the web app. Your file goes from your browser straight to the Mbiu API.</li>
                <li>Grafana Cloud, Sentry, PostHog: counts, IDs, durations, error categories and versions only.</li>
                <li>Cloudflare Turnstile: bot-check token only.</li>
              </ul>
            </li>
          </ul>
        </div>
      )}

      <div className="consent-control">
        <label className="consent-label" htmlFor="consent-checkbox">
          <input
            id="consent-checkbox"
            type="checkbox"
            checked={consentChecked}
            onChange={(e) => onConsentChange(e.target.checked)}
            required
            className="consent-checkbox"
          />
          <span>
            I confirm that I am authorised to submit this document and agree to
            it being evaluated according to the privacy notice above.
          </span>
        </label>
      </div>
    </section>
  );
}
