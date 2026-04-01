import { useEffect, useState } from "react";
import { getRiskEvents, type RiskEvent } from "../api";

export function RiskPage() {
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getRiskEvents()
      .then(setEvents)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load risk events"));
  }, []);

  return (
    <section className="card">
      <h2>Risk</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Symbol</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{event.severity}</td>
              <td>{event.symbol ?? "-"}</td>
              <td>{event.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
