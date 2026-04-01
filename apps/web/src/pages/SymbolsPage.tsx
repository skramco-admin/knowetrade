import { useEffect, useState } from "react";
import { getSymbols, type SymbolRow } from "../api";

export function SymbolsPage() {
  const [symbols, setSymbols] = useState<SymbolRow[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getSymbols()
      .then(setSymbols)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load symbols"));
  }, []);

  return (
    <section className="card">
      <h2>ETF Universe</h2>
      <p>
        Active ETFs in the <code>etf_trend</code> strategy bucket are monitored by the worker.
      </p>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Asset Class</th>
            <th>Strategy Bucket</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {symbols.map((symbol) => (
            <tr key={symbol.ticker}>
              <td>{symbol.ticker}</td>
              <td>{symbol.asset_class}</td>
              <td>{symbol.strategy_bucket}</td>
              <td>{symbol.is_active ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
