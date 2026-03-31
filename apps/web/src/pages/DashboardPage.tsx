import { useEffect, useState } from "react";
import { getDashboardSummary, type DashboardSummary } from "../api";

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary().then(setSummary);
  }, []);

  return (
    <section className="card">
      <h2>Dashboard</h2>
      <p>v1 focus: long-only, low-frequency ETF automation.</p>
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
      </div>
    </section>
  );
}
