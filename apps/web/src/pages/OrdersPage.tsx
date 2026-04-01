import { useEffect, useState } from "react";
import { getOrders, type Order } from "../api";

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
      <h2>Orders</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Status</th>
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
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
