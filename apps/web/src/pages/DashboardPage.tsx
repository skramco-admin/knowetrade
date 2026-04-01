import { useEffect, useState } from "react";
import { getAccountMetrics, getDashboardSummary, type AccountMetrics, type DashboardSummary } from "../api";
import { getTradingCronCountdowns, type CronCountdown } from "../schedule";

function formatUsd(value: number | undefined): string {
  if (value === undefined) {
    return "--";
  }
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function formatPct(value: number | undefined): string {
  if (value === undefined) {
    return "--";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [account, setAccount] = useState<AccountMetrics | null>(null);
  const [cronCountdowns, setCronCountdowns] = useState<CronCountdown[]>(getTradingCronCountdowns());
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load dashboard summary"));
    getAccountMetrics()
      .then(setAccount)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load account metrics"));

    const timer = window.setInterval(() => {
      setCronCountdowns(getTradingCronCountdowns());
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const pnl = account?.day_pnl;
  const pnlLabel = pnl === undefined ? "--" : pnl >= 0 ? "Up today" : "Down today";

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
        <article className="metric">
          <h3>Portfolio Equity</h3>
          <p>{formatUsd(account?.equity)}</p>
        </article>
        <article className="metric">
          <h3>Cash</h3>
          <p>{formatUsd(account?.cash)}</p>
        </article>
        <article className="metric">
          <h3>Buying Power</h3>
          <p>{formatUsd(account?.buying_power)}</p>
        </article>
        <article className="metric">
          <h3>{pnlLabel}</h3>
          <p>
            {formatUsd(account?.day_pnl)} ({formatPct(account?.day_pnl_pct)})
          </p>
        </article>
      </div>
      <h3 style={{ marginTop: "1rem" }}>Next Automated Checks</h3>
      <ul className="list">
        {cronCountdowns.map((item) => (
          <li key={item.label}>
            <strong>{item.label}:</strong> in {item.countdown} (local: {item.nextRunLocal})
          </li>
        ))}
      </ul>
    </section>
  );
}
