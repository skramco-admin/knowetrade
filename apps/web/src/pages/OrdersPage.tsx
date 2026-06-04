import { useEffect, useState } from "react";
import { getOrders, type Order } from "../api";
import { formatDateTime, formatOrderPnl, formatUsd } from "../format";

function orderSubmittedAt(order: Order): string {
  return formatDateTime(order.submitted_at ?? order.created_at);
}

function orderActivityAt(order: Order): string {
  return formatDateTime(order.filled_at ?? order.updated_at);
}

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getOrders()
      .then(setOrders)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load orders"));
  }, []);

  return (
    <section className="card">
      <h2>Trades</h2>
      <p className="muted">Orders actually sent to Alpaca paper trading.</p>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Status</th>
            <th>Realized P&amp;L</th>
            <th>Fill price</th>
            <th>Submitted</th>
            <th>Filled / updated</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td>{order.id}</td>
              <td>{order.symbol}</td>
              <td>{order.side}</td>
              <td>{order.qty}</td>
              <td>{order.status}</td>
              <td
                className={
                  order.realized_pnl_usd === undefined
                    ? ""
                    : order.realized_pnl_usd < 0
                      ? "pnl-negative"
                      : "pnl-positive"
                }
              >
                {formatOrderPnl(order)}
              </td>
              <td>{order.filled_avg_price !== undefined ? formatUsd(order.filled_avg_price) : "—"}</td>
              <td>{orderSubmittedAt(order)}</td>
              <td>{orderActivityAt(order)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
