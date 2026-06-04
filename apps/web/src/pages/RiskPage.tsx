import { useEffect, useMemo, useState } from "react";
import { getPositions, getProposedOrders, getRiskEvents, type RiskEvent } from "../api";
import { AlertList, StatusPill } from "../components/OperatorUi";
import { buildRiskWatchItems, riskSeverityLevel } from "../dashboardInsights";
import { formatDateTime } from "../format";

export function RiskPage() {
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [positions, setPositions] = useState<Awaited<ReturnType<typeof getPositions>>>([]);
  const [proposed, setProposed] = useState<Awaited<ReturnType<typeof getProposedOrders>>>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getRiskEvents(), getPositions(), getProposedOrders()])
      .then(([riskRows, positionRows, proposedRows]) => {
        setEvents(riskRows);
        setPositions(positionRows);
        setProposed(proposedRows);
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load risk events"))
      .finally(() => setLoading(false));
  }, []);

  const watchItems = useMemo(() => buildRiskWatchItems(positions, proposed, events), [positions, proposed, events]);

  return (
    <section className="card">
      <h2>Risk</h2>
      <p className="muted">
        Warnings when broker holdings drift from strategy intent, orders fail checks, or reconciliation finds mismatches.
      </p>
      {error ? <p role="alert" className="error">API error: {error}</p> : null}

      <h3 style={{ marginTop: "1.25rem" }}>Right now</h3>
      <AlertList items={watchItems} />

      <h3 style={{ marginTop: "1.25rem" }}>Event history</h3>
      {loading ? <p className="muted">Loading risk events…</p> : null}
      {!loading && events.length === 0 ? (
        <p className="muted">
          No stored risk events yet. After the next weekday reconciliation cron, mismatches (e.g. unexpected broker
          positions like IVV/VTI) will appear here.
        </p>
      ) : null}
      {events.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Symbol</th>
              <th>What happened</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>
                  <StatusPill
                    status={riskSeverityLevel(event.severity)}
                    label={event.severity || "warning"}
                  />
                </td>
                <td>{event.symbol ?? "—"}</td>
                <td>{event.reason}</td>
                <td>{formatDateTime(event.event_time ?? event.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
