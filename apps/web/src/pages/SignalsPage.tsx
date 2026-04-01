import { useEffect, useState } from "react";
import { getSignals, type Signal } from "../api";

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getSignals()
      .then(setSignals)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load signals"));
  }, []);

  return (
    <section className="card">
      <h2>Signals</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Type</th>
            <th>Strength</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
            <tr key={signal.id}>
              <td>{signal.symbol}</td>
              <td>{signal.signal}</td>
              <td>{signal.strength}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
