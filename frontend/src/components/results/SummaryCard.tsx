import React from "react";
import type { Summary } from "@/lib/api/generated/types.gen";

interface SummaryCardProps {
  summary: Summary;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({ summary }) => {
  return (
    <section className="evaluation-summary-card" aria-label="Contract Summary">
      <header className="summary-card-header">
        <h2 className="summary-title">Evaluation Summary & Top Questions</h2>
        <p className="summary-subtitle">
          Key points to clarify before signing this contract.
        </p>
      </header>

      {summary.top_asks && summary.top_asks.length > 0 && (
        <div className="summary-section top-asks">
          <h3 className="section-title">Top 3 Questions to Ask</h3>
          <ol className="top-asks-list">
            {summary.top_asks.map((ask, index) => (
              <li key={index} className="top-ask-item">
                <span className="ask-index">{index + 1}</span>
                <p className="ask-text">“{ask.question}”</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {summary.missing_protections.length > 0 && (
        <div className="summary-section missing-protections">
          <h3 className="section-title">Missing from your contract</h3>
          <p className="summary-subtitle">
            The reviewed standard protects you here, but your contract doesn&apos;t say anything about it.
          </p>
          <ul className="top-asks-list">
            {summary.missing_protections.map((item) => (
              <li key={item.template_id} className="top-ask-item">
                <p className="ask-text">
                  <strong>{item.title}:</strong> “{item.ask_them}”
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.good_news && summary.good_news.length > 0 && (
        <div className="summary-section good-news">
          <h3 className="section-title">Good News in Your Contract</h3>
          <ul className="good-news-list">
            {summary.good_news.map((note, index) => (
              <li key={index} className="good-news-item">
                <span className="good-news-icon">✓</span>
                <p className="good-news-text">{note.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <footer className="summary-footer">
        <div className="summary-meta-item">
          <span className="meta-label">Typical clauses:</span>
          <span className="meta-value">{summary.matches_count} clauses</span>
        </div>
        <div className="summary-meta-item">
          <span className="meta-label">Model Engine:</span>
          <span className="meta-value">{summary.versions.model}</span>
        </div>
      </footer>
    </section>
  );
};
