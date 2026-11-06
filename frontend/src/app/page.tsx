import Link from "next/link";
import { Suspense } from "react";
import { API_URL } from "@/lib/env";

async function apiStatus(): Promise<string> {
  try {
    const response = await fetch(`${API_URL}/healthz`, { cache: "no-store" });
    return response.ok ? "healthy" : `error ${response.status}`;
  } catch {
    return `unreachable at ${API_URL}`;
  }
}

async function ApiStatusBadge() {
  const status = await apiStatus();
  const isHealthy = status === "healthy";
  return (
    <span
      className={`status-pill ${isHealthy ? "match" : "failed"}`}
      style={{ marginLeft: "0.5rem" }}
    >
      Backend: {status}
    </span>
  );
}

export default function Home() {
  return (
    <main className="page-wrapper">
      <header className="header-section">
        <h1 className="brand-title">Mbiu</h1>
        <p className="brand-tagline">
          Understand a music contract before you sign it.
        </p>
      </header>

      <section className="starter-panel" aria-label="Quick Actions">
        <div className="starter-card">
          <h3>Live Results Stream</h3>
          <p>
            Inspect the live NDJSON streaming pipeline. View real-time clause extraction,
            progress tracking, and risk cards sorted in impact order.
          </p>
          <Link href="/results" className="start-demo-btn" style={{ textDecoration: "none" }}>
            Open Live Results Page →
          </Link>
        </div>

        <div className="starter-card">
          <div style={{ display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>System Status:</span>
            <Suspense fallback={<span className="status-pill pending" style={{ marginLeft: "0.5rem" }}>Checking API…</span>}>
              <ApiStatusBadge />
            </Suspense>
          </div>
        </div>
      </section>
    </main>
  );
}
