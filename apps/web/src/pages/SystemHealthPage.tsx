import { useEffect, useState } from "react";
import { getSystemHealth, type SystemHealth } from "../api";

export function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getSystemHealth()
      .then(setHealth)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load system health"));
  }, []);

  return (
    <section className="card">
      <h2>System Health</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <ul className="list">
        <li>
          <strong>Status:</strong> {health?.status ?? "checking"}
        </li>
        <li>
          <strong>Checked:</strong> {health?.checked_at ?? "-"}
        </li>
        <li>
          <strong>App mode:</strong> {health?.app_mode ?? "-"}
        </li>
        <li>
          <strong>Database OK:</strong> {String(health?.database_ok ?? false)}
        </li>
        <li>
          <strong>Alpaca paper endpoint:</strong> {String(health?.alpaca_paper_endpoint ?? false)}
        </li>
        <li>
          <strong>Alpaca auth OK:</strong> {String(health?.alpaca_auth_ok ?? false)}
        </li>
        <li>
          <strong>Trading enabled:</strong> {String(health?.trading_enabled ?? false)}
        </li>
        <li>
          <strong>Order submission enabled:</strong> {String(health?.enable_order_submission ?? false)}
        </li>
        <li>
          <strong>Active ETF symbols:</strong> {health?.active_etf_symbols ?? 0}
        </li>
        <li>
          <strong>Monitored tickers:</strong> {health?.monitored_tickers?.join(", ") ?? "-"}
        </li>
      </ul>
    </section>
  );
}
