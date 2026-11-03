import { Suspense } from "react";

import { API_URL } from "@/lib/env";

async function apiStatus(): Promise<string> {
  try {
    const response = await fetch(`${API_URL}/healthz`, { cache: "no-store" });
    return response.ok ? "ok" : `error ${response.status}`;
  } catch {
    return `unreachable at ${API_URL}`;
  }
}

async function ApiStatus() {
  return <p>API: {await apiStatus()}</p>;
}

export default function Home() {
  return (
    <main>
      <h1>Mbiu</h1>
      <Suspense fallback={<p>API: checking…</p>}>
        <ApiStatus />
      </Suspense>
    </main>
  );
}
