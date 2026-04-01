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
  order_type?: string;
  submitted_at?: string;
  filled_at?: string;
  updated_at?: string;
  created_at?: string;
};

export type Signal = {
  id: number;
  symbol: string;
  signal: string;
  strength: number;
  reason?: string;
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
  checked_at: string;
  active_etf_symbols: number;
  monitored_tickers: string[];
  app_mode?: string;
  database_ok?: boolean;
  alpaca_paper_endpoint?: boolean;
  alpaca_auth_ok?: boolean;
  trading_enabled?: boolean;
  enable_order_submission?: boolean;
};

export type JobRun = {
  id: number;
  job_name: string;
  status: string;
  started_at?: string;
  created_at?: string;
};

export type ProposedOrder = {
  id: number;
  symbol: string;
  action: string;
  target_weight: number;
  reason?: string;
  created_at?: string;
};

export type DashboardSummary = {
  activePositions: number;
  openOrders: number;
  latestSignals: number;
  recentRiskEvents: number;
  activeEtfSymbols: number;
  recentJobRuns: number;
  proposedOrders: number;
};

export type SymbolRow = {
  ticker: string;
  asset_class: string;
  strategy_bucket: string;
  is_active: boolean;
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

function activeEtfTrendSymbols(symbols: SymbolRow[]): SymbolRow[] {
  return symbols.filter(
    (symbol) =>
      symbol.is_active &&
      symbol.asset_class.toUpperCase() === "ETF" &&
      symbol.strategy_bucket === "etf_trend",
  );
}

export async function getSymbols(): Promise<SymbolRow[]> {
  return fetchApi<SymbolRow[]>("/symbols");
}

export async function getSystemHealth(): Promise<SystemHealth> {
  const [symbols, deps] = await Promise.all([getSymbols(), fetchApi<Record<string, unknown>>("/health/deps")]);
  const monitored = activeEtfTrendSymbols(symbols);
  return {
    status: String(deps.status ?? "unknown"),
    checked_at: new Date().toISOString(),
    active_etf_symbols: monitored.length,
    monitored_tickers: monitored.map((symbol) => symbol.ticker),
    app_mode: String(deps.app_mode ?? ""),
    database_ok: Boolean(deps.database_ok),
    alpaca_paper_endpoint: Boolean(deps.alpaca_paper_endpoint),
    alpaca_auth_ok: Boolean(deps.alpaca_auth_ok),
    trading_enabled: Boolean(deps.trading_enabled),
    enable_order_submission: Boolean(deps.enable_order_submission),
  };
}

export async function getPositions(): Promise<Position[]> {
  return fetchApi<Position[]>("/positions");
}

export async function getOrders(): Promise<Order[]> {
  return fetchApi<Order[]>("/orders");
}

export async function getSignals(): Promise<Signal[]> {
  return fetchApi<Signal[]>("/signals");
}

export async function getRiskEvents(): Promise<RiskEvent[]> {
  return fetchApi<RiskEvent[]>("/risk-events");
}

export async function getJobRuns(): Promise<JobRun[]> {
  return fetchApi<JobRun[]>("/job-runs");
}

export async function getProposedOrders(): Promise<ProposedOrder[]> {
  return fetchApi<ProposedOrder[]>("/proposed-orders");
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const [positions, orders, signals, riskEvents, symbols, jobRuns, proposedOrders] = await Promise.all([
    getPositions(),
    getOrders(),
    getSignals(),
    getRiskEvents(),
    getSymbols(),
    getJobRuns(),
    getProposedOrders(),
  ]);
  const monitored = activeEtfTrendSymbols(symbols);

  return {
    activePositions: positions.length,
    openOrders: orders.filter((order) => order.status !== "filled").length,
    latestSignals: signals.length,
    recentRiskEvents: riskEvents.length,
    activeEtfSymbols: monitored.length,
    recentJobRuns: jobRuns.length,
    proposedOrders: proposedOrders.length,
  };
}
