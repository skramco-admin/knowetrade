export type Position = {
  id: number;
  symbol: string;
  qty: number;
  avg_price: number;
  updated_at?: string;
};

export type Order = {
  id: number;
  symbol: string;
  qty: number;
  side: string;
  status: string;
  created_at?: string;
};

export type Signal = {
  id: number;
  symbol: string;
  signal_type: string;
  strength: number;
  signal_time?: string;
};

export type RiskEvent = {
  id: number;
  symbol?: string;
  severity: string;
  reason: string;
  event_time?: string;
};

export type SystemHealth = {
  status: string;
  source: string;
  checked_at: string;
};

export type DashboardSummary = {
  activePositions: number;
  openOrders: number;
  latestSignals: number;
  recentRiskEvents: number;
};

// Frontend is API-only by design. Broker endpoints are never called here.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY ?? "";

async function fetchApi<T>(path: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (ADMIN_API_KEY) {
    headers["x-admin-key"] = ADMIN_API_KEY;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`API request failed: ${path} (${response.status})`);
  }
  return (await response.json()) as T;
}

const placeholderPositions: Position[] = [
  { id: 1, symbol: "SPY", qty: 4, avg_price: 522.14, updated_at: "2026-03-31T13:55:00Z" },
  { id: 2, symbol: "QQQ", qty: 2, avg_price: 441.62, updated_at: "2026-03-31T13:55:00Z" },
];

const placeholderOrders: Order[] = [
  { id: 101, symbol: "IVV", qty: 1, side: "buy", status: "accepted", created_at: "2026-03-31T13:30:00Z" },
  { id: 102, symbol: "VTI", qty: 1, side: "buy", status: "filled", created_at: "2026-03-31T13:32:00Z" },
];

const placeholderSignals: Signal[] = [
  { id: 201, symbol: "SPY", signal_type: "momentum_buy", strength: 0.74, signal_time: "2026-03-31T13:20:00Z" },
  { id: 202, symbol: "QQQ", signal_type: "mean_revert_buy", strength: 0.61, signal_time: "2026-03-31T13:21:00Z" },
];

const placeholderRiskEvents: RiskEvent[] = [
  {
    id: 301,
    symbol: "XLK",
    severity: "warning",
    reason: "Order blocked by max notional rule",
    event_time: "2026-03-31T13:26:00Z",
  },
];

export async function getSystemHealth(): Promise<SystemHealth> {
  try {
    const response = await fetchApi<{ status: string }>("/health");
    return {
      status: response.status,
      source: "api",
      checked_at: new Date().toISOString(),
    };
  } catch {
    return {
      status: "degraded",
      source: "placeholder",
      checked_at: new Date().toISOString(),
    };
  }
}

export async function getPositions(): Promise<Position[]> {
  try {
    return await fetchApi<Position[]>("/admin/positions");
  } catch {
    return placeholderPositions;
  }
}

export async function getOrders(): Promise<Order[]> {
  try {
    return await fetchApi<Order[]>("/admin/orders");
  } catch {
    return placeholderOrders;
  }
}

export async function getSignals(): Promise<Signal[]> {
  try {
    return await fetchApi<Signal[]>("/admin/signals");
  } catch {
    return placeholderSignals;
  }
}

export async function getRiskEvents(): Promise<RiskEvent[]> {
  try {
    return await fetchApi<RiskEvent[]>("/admin/risk-events");
  } catch {
    return placeholderRiskEvents;
  }
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const [positions, orders, signals, riskEvents] = await Promise.all([
    getPositions(),
    getOrders(),
    getSignals(),
    getRiskEvents(),
  ]);
  return {
    activePositions: positions.length,
    openOrders: orders.filter((order) => order.status !== "filled").length,
    latestSignals: signals.length,
    recentRiskEvents: riskEvents.length,
  };
}
