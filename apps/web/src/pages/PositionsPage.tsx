import { useEffect, useState } from "react";
import { getPositions, type Position } from "../api";

export function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getPositions()
      .then(setPositions)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load positions"));
  }, []);

  return (
    <section className="card">
      <h2>Positions</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Qty</th>
            <th>Avg Price</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.id}>
              <td>{position.symbol}</td>
              <td>{position.qty}</td>
              <td>{position.avg_price}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
