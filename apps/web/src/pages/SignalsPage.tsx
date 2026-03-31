import { useEffect, useState } from "react";
import { getSignals, type Signal } from "../api";

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);

  useEffect(() => {
    getSignals().then(setSignals);
  }, []);

  return (
    <section className="card">
      <h2>Signals</h2>
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
              <td>{signal.signal_type}</td>
              <td>{signal.strength}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
