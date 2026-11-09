"use client";

import React from "react";
import { CopyButton } from "./CopyButton";

export interface CardQuestionsProps {
  askThem?: string | null;
  whatsappShareUrl: string;
}

export const CardQuestions: React.FC<CardQuestionsProps> = ({
  askThem,
  whatsappShareUrl,
}) => {
  if (!askThem) return null;

  return (
    <section className="card-section card-ask-them-section" data-testid="ask-them-section">
      <div className="ask-them-header">
        <h4 className="card-section-title">Questions you could ask</h4>
        <div className="ask-them-actions">
          <CopyButton
            text={askThem}
            label="📋 Copy"
            copiedLabel="✓ Copied"
            className="action-btn copy-action-btn"
          />
          <a
            href={whatsappShareUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="action-btn whatsapp-action-btn"
            aria-label="Share question to WhatsApp"
          >
            <span className="whatsapp-icon" aria-hidden="true">
              💬
            </span>
            <span>WhatsApp</span>
          </a>
        </div>
      </div>
      <p className="ask-them-text">“{askThem}”</p>
    </section>
  );
};
