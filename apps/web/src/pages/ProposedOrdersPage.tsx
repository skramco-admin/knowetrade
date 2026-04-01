import { useEffect, useState } from "react";
import { getProposedOrders, type ProposedOrder } from "../api";

export function ProposedOrdersPage() {
  const [rows, setRows] = useState<ProposedOrder[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getProposedOrders()
      .then(setRows)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load proposed orders"));
  }, []);

  return (
    <section className="card">
      <h2>Proposed Orders</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Action</th>
            <th>Target Weight</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.symbol}</td>
              <td>{row.action}</td>
              <td>{row.target_weight}</td>
              <td>{row.reason ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
