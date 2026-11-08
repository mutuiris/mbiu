"use client";

import React from "react";
import Link from "next/link";

interface PrivacyNoticeProps {
  consentChecked: boolean;
  onConsentChange: (checked: boolean) => void;
}

export function PrivacyNotice({
  consentChecked,
  onConsentChange,
}: PrivacyNoticeProps) {
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
        contract is evaluated <strong>instantly</strong>, we{" "}
        <strong>never store</strong> your contract.
      </p>

      <Link
        href="/privacy"
        className="text-toggle-btn inline-block"
      >
        Read full privacy &amp; data transfer details
      </Link>

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
