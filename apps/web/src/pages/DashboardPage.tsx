import { useEffect, useState } from "react";
import { getDashboardSummary, type DashboardSummary } from "../api";

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load dashboard summary"));
  }, []);

  return (
    <section className="card">
      <h2>Dashboard</h2>
      <p>v1 focus: long-only, low-frequency ETF automation.</p>
      {error ? <p role="alert">API error: {error}</p> : null}
      <div className="grid">
        <article className="metric">
          <h3>Active Positions</h3>
          <p>{summary?.activePositions ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Open Orders</h3>
          <p>{summary?.openOrders ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Recent Signals</h3>
          <p>{summary?.latestSignals ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Risk Events</h3>
          <p>{summary?.recentRiskEvents ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Active ETF Symbols</h3>
          <p>{summary?.activeEtfSymbols ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Recent Job Runs</h3>
          <p>{summary?.recentJobRuns ?? "--"}</p>
        </article>
        <article className="metric">
          <h3>Proposed Orders</h3>
          <p>{summary?.proposedOrders ?? "--"}</p>
        </article>
      </div>
    </section>
  );
}
