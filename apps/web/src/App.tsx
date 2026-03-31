import { useEffect, useState } from "react";
import { getApiHealth } from "./api";

export function App() {
  const [apiStatus, setApiStatus] = useState<string>("checking");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApiHealth()
      .then((data) => setApiStatus(data.status))
      .catch((err: unknown) => {
        setApiStatus("unreachable");
        setError(err instanceof Error ? err.message : "Unknown API error");
      });
  }, []);

  return (
    <main className="container">
      <h1>KnoweTrade Dashboard</h1>
      <p>v1 focus: long-only, low-frequency ETF automation.</p>
      <section className="card">
        <h2>System health</h2>
        <p>API status: {apiStatus}</p>
        {error && <p className="error">{error}</p>}
      </section>
      <section className="card">
        <h2>Architecture guardrails</h2>
        <ul>
          <li>Frontend calls API endpoints only.</li>
          <li>Broker access happens in backend worker services.</li>
          <li>Risk checks run before order placement.</li>
        </ul>
      </section>
    </main>
  );
}
