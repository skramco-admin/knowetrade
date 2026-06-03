import { useEffect, useMemo, useState } from "react";
import { getJobRuns, getSystemHealth } from "../api";
import { buildHealthChecks } from "../dashboardInsights";
import { HealthCheckList } from "../components/OperatorUi";

export function SystemHealthPage() {
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getSystemHealth>> | null>(null);
  const [jobRuns, setJobRuns] = useState<Awaited<ReturnType<typeof getJobRuns>>>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    Promise.all([getSystemHealth(), getJobRuns()])
      .then(([healthData, runs]) => {
        setHealth(healthData);
        setJobRuns(runs);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load system health"));
  }, []);

  const checks = useMemo(() => (health ? buildHealthChecks(health, jobRuns) : []), [health, jobRuns]);

  return (
    <section className="card">
      <h2>Is it working?</h2>
      <p className="muted">Green = fine. Check = review soon. Fix = something is blocking trades.</p>
      {error ? <p role="alert" className="error">API error: {error}</p> : null}
      <HealthCheckList checks={checks} />
      {health ? (
        <ul className="list health-meta">
          <li>
            <strong>App mode:</strong> {health.app_mode ?? "—"}
          </li>
          <li>
            <strong>Active ETF symbols:</strong> {health.active_etf_symbols ?? 0}
          </li>
          <li>
            <strong>Monitored tickers:</strong> {health.monitored_tickers?.join(", ") ?? "—"}
          </li>
          <li>
            <strong>Last checked:</strong> {health.checked_at ?? "—"}
          </li>
        </ul>
      ) : null}
    </section>
  );
}
