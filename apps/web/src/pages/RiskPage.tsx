import { useEffect, useState } from "react";
import { getRiskEvents, type RiskEvent } from "../api";

export function RiskPage() {
  const [events, setEvents] = useState<RiskEvent[]>([]);

  useEffect(() => {
    getRiskEvents().then(setEvents);
  }, []);

  return (
    <section className="card">
      <h2>Risk</h2>
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
