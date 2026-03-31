import { useEffect, useState } from "react";
import { getSystemHealth, type SystemHealth } from "../api";

export function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    getSystemHealth().then(setHealth);
  }, []);

  return (
    <section className="card">
      <h2>System Health</h2>
      <ul className="list">
        <li>
          <strong>Status:</strong> {health?.status ?? "checking"}
        </li>
        <li>
          <strong>Source:</strong> {health?.source ?? "unknown"}
        </li>
        <li>
          <strong>Checked:</strong> {health?.checked_at ?? "-"}
        </li>
      </ul>
    </section>
  );
}
