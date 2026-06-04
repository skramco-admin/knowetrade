import type { AccountMetrics, JobRun, Order, Position, ProposedOrder, RiskEvent, SystemHealth } from "./api";
import { EXECUTION_JOB_NAMES, friendlyJobName, STRATEGY_JOB_NAMES } from "./jobs";
import { formatOrderPnl, formatRelativeTime, isTodayUtc, isTradingWeekdayUtc, parseIso, startOfUtcDay } from "./format";

export type StatusLevel = "ok" | "warn" | "bad";
export type AlertSeverity = StatusLevel | "info";

export type HealthCheck = {
  id: string;
  label: string;
  status: StatusLevel;
  message: string;
  fixHint?: string;
};

export type Alert = {
  severity: AlertSeverity;
  message: string;
  detail?: string;
};

export type ActivityItem = {
  at: Date;
  kind: "job" | "order";
  status: StatusLevel;
  message: string;
};

export type TodayStats = {
  strategyCyclesSucceeded: number;
  strategyCyclesFailed: number;
  executionRunsSucceeded: number;
  enterCount: number;
  exitCount: number;
  holdCount: number;
  ordersSubmitted: number;
  ordersFilled: number;
  buysToday: number;
  sellsToday: number;
};

export type PortfolioIntent = {
  holding: string[];
  wantToBuy: string[];
  wantToSell: string[];
};

export type AccountOverview = {
  totalValue: number;
  cash: number;
  inMarket: number;
  openPositions: number;
  startingEquity: number;
  dayPnl: number;
  dayPnlPct: number;
  lifetimePnl: number;
  lifetimePnlPct: number;
  realizedPnlTracked: number;
  overallStatus: StatusLevel;
  overallLabel: string;
  dayStatus: StatusLevel;
  dayLabel: string;
};

export function buildAccountOverview(
  account: AccountMetrics | null,
  positions: Position[],
  orders: Order[],
): AccountOverview | null {
  if (!account) {
    return null;
  }

  const realizedPnlTracked = orders
    .filter((order) => order.side.toLowerCase() === "sell" && order.realized_pnl_usd !== undefined)
    .reduce((sum, order) => sum + (order.realized_pnl_usd ?? 0), 0);

  const lifetimePnl = account.lifetime_pnl ?? account.equity - (account.starting_equity ?? 100_000);
  const lifetimePnlPct =
    account.lifetime_pnl_pct ??
    (account.starting_equity > 0 ? lifetimePnl / account.starting_equity : 0);
  const dayPnl = account.day_pnl ?? 0;
  const dayPnlPct = account.day_pnl_pct ?? 0;

  const overallStatus: StatusLevel = lifetimePnl > 0 ? "ok" : lifetimePnl < 0 ? "bad" : "warn";
  const dayStatus: StatusLevel = dayPnl > 0 ? "ok" : dayPnl < 0 ? "bad" : "warn";

  return {
    totalValue: account.equity,
    cash: account.cash,
    inMarket: account.long_market_value ?? Math.max(account.equity - account.cash, 0),
    openPositions: positions.filter((position) => position.qty > 0).length,
    startingEquity: account.starting_equity ?? 100_000,
    dayPnl,
    dayPnlPct,
    lifetimePnl,
    lifetimePnlPct,
    realizedPnlTracked,
    overallStatus,
    overallLabel: lifetimePnl > 0 ? "Account up overall" : lifetimePnl < 0 ? "Account down overall" : "Flat overall",
    dayStatus,
    dayLabel: dayPnl > 0 ? "Up today" : dayPnl < 0 ? "Down today" : "Flat today",
  };
}

export type GlanceSummary = {
  overallStatus: StatusLevel;
  overallLabel: string;
  lastJobLabel: string;
  lastJobRelative: string;
  lastJobStatus: StatusLevel;
  tradesSummary: string;
  pnlSummary: string;
  nextCronLabel: string;
};

export function latestProposedBySymbol(rows: ProposedOrder[]): ProposedOrder[] {
  const bySymbol = new Map<string, ProposedOrder>();
  for (const row of rows) {
    const key = row.symbol.toUpperCase();
    if (!bySymbol.has(key)) {
      bySymbol.set(key, row);
    }
  }
  return [...bySymbol.values()].sort((a, b) => a.symbol.localeCompare(b.symbol));
}

export function buildRiskWatchItems(
  positions: Position[],
  proposed: ProposedOrder[],
  riskEvents: RiskEvent[],
): Alert[] {
  const items: Alert[] = [];
  const latest = latestProposedBySymbol(proposed);
  const intended = new Set(latest.filter((row) => row.action === "ENTER" || row.action === "HOLD").map((row) => row.symbol));
  const heldSymbols = positions.filter((position) => position.qty > 0).map((position) => position.symbol.toUpperCase());
  const orphanHeld = heldSymbols.filter((symbol) => latest.length > 0 && !intended.has(symbol));

  if (orphanHeld.length > 0) {
    items.push({
      severity: "warn",
      message: `Positions not in target portfolio: ${orphanHeld.join(", ")}`,
      detail: "Bot may propose EXIT on the next strategy cycle.",
    });
  }

  const latestMismatch = riskEvents.find(
    (event) =>
      event.reason.toLowerCase().includes("reconcile") || event.reason.toLowerCase().includes("mismatch"),
  );
  if (latestMismatch) {
    items.push({
      severity: latestMismatch.severity === "critical" ? "bad" : "warn",
      message: latestMismatch.reason,
      detail: latestMismatch.symbol ? `Symbol: ${latestMismatch.symbol}` : "Portfolio-wide issue",
    });
  }

  if (items.length === 0) {
    items.push({
      severity: "ok",
      message: "No active risk issues detected right now.",
      detail: "New warnings appear here after reconciliation or broker mismatches.",
    });
  }

  return items;
}

export function riskSeverityLevel(severity: string): StatusLevel {
  const normalized = severity.toLowerCase();
  if (normalized === "critical" || normalized === "error") {
    return "bad";
  }
  if (normalized === "warning" || normalized === "warn") {
    return "warn";
  }
  return "ok";
}

export function buildPortfolioIntent(proposed: ProposedOrder[]): PortfolioIntent {
  const latest = latestProposedBySymbol(proposed);
  return {
    holding: latest.filter((row) => row.action === "HOLD").map((row) => row.symbol),
    wantToBuy: latest.filter((row) => row.action === "ENTER").map((row) => row.symbol),
    wantToSell: latest.filter((row) => row.action === "EXIT").map((row) => row.symbol),
  };
}

function isSuccessStatus(status: string): boolean {
  return status === "success";
}

function isFailureStatus(status: string): boolean {
  return status === "failed" || status === "completed_with_errors";
}

export function buildTodayStats(jobRuns: JobRun[], proposed: ProposedOrder[], orders: Order[]): TodayStats {
  const todayRuns = jobRuns.filter((run) => isTodayUtc(run.started_at ?? run.created_at));
  const strategyCyclesSucceeded = todayRuns.filter(
    (run) => STRATEGY_JOB_NAMES.has(run.job_name) && isSuccessStatus(run.status),
  ).length;
  const strategyCyclesFailed = todayRuns.filter(
    (run) => STRATEGY_JOB_NAMES.has(run.job_name) && isFailureStatus(run.status),
  ).length;
  const executionRunsSucceeded = todayRuns.filter(
    (run) => EXECUTION_JOB_NAMES.has(run.job_name) && isSuccessStatus(run.status),
  ).length;

  const latest = latestProposedBySymbol(proposed);
  const todayOrders = orders.filter((order) =>
    isTodayUtc(order.submitted_at ?? order.created_at ?? order.filled_at),
  );

  return {
    strategyCyclesSucceeded,
    strategyCyclesFailed,
    executionRunsSucceeded,
    enterCount: latest.filter((row) => row.action === "ENTER").length,
    exitCount: latest.filter((row) => row.action === "EXIT").length,
    holdCount: latest.filter((row) => row.action === "HOLD").length,
    ordersSubmitted: todayOrders.length,
    ordersFilled: todayOrders.filter((order) => order.status === "filled").length,
    buysToday: todayOrders.filter((order) => order.side.toLowerCase() === "buy").length,
    sellsToday: todayOrders.filter((order) => order.side.toLowerCase() === "sell").length,
  };
}

export function buildHealthChecks(health: SystemHealth, jobRuns: JobRun[]): HealthCheck[] {
  const checks: HealthCheck[] = [];
  const latestRun = jobRuns[0];

  checks.push({
    id: "database",
    label: "Database",
    status: health.database_ok ? "ok" : "bad",
    message: health.database_ok ? "Connected — bot can read and write data." : "Cannot reach the database.",
    fixHint: health.database_ok ? undefined : "Set DATABASE_URL on every Render cron and redeploy.",
  });

  checks.push({
    id: "alpaca",
    label: "Alpaca paper account",
    status: health.alpaca_auth_ok && health.alpaca_paper_endpoint ? "ok" : "bad",
    message:
      health.alpaca_auth_ok && health.alpaca_paper_endpoint
        ? "Connected to Alpaca paper trading."
        : "Broker connection failed or not in paper mode.",
    fixHint:
      health.alpaca_auth_ok && health.alpaca_paper_endpoint
        ? undefined
        : "Check ALPACA_API_KEY, ALPACA_API_SECRET, and ALPACA_BASE_URL on trading crons.",
  });

  checks.push({
    id: "trading",
    label: "Trading enabled",
    status: health.trading_enabled ? "ok" : "warn",
    message: health.trading_enabled ? "Bot is allowed to trade." : "Trading is turned off — nothing will execute.",
    fixHint: health.trading_enabled ? undefined : "Set TRADING_ENABLED=true on trading crons.",
  });

  checks.push({
    id: "submission",
    label: "Order submission",
    status: health.enable_order_submission ? "ok" : "warn",
    message: health.enable_order_submission
      ? "Bot will send orders to Alpaca when proposals exist."
      : "Proposals only — orders will NOT be sent.",
    fixHint: health.enable_order_submission ? undefined : "Set ENABLE_ORDER_SUBMISSION=true on strategy and order-submit crons.",
  });

  if (latestRun) {
    const runStatus: StatusLevel = isSuccessStatus(latestRun.status)
      ? "ok"
      : isFailureStatus(latestRun.status)
        ? "bad"
        : "warn";
    checks.push({
      id: "last_job",
      label: "Latest automation run",
      status: runStatus,
      message: `${friendlyJobName(latestRun.job_name)} — ${latestRun.status} (${formatRelativeTime(latestRun.started_at ?? latestRun.created_at)})`,
      fixHint: runStatus === "bad" ? "Open Automation log or Render cron logs for the failed job." : undefined,
    });
  } else {
    checks.push({
      id: "last_job",
      label: "Latest automation run",
      status: "warn",
      message: "No job runs recorded yet.",
      fixHint: "Trigger a manual run on a Render cron or wait for the next scheduled cycle.",
    });
  }

  return checks;
}

export function buildAlerts(
  health: SystemHealth,
  jobRuns: JobRun[],
  proposed: ProposedOrder[],
  orders: Order[],
  riskEvents: RiskEvent[],
  positions: { symbol: string }[],
): Alert[] {
  const alerts: Alert[] = [];
  const now = new Date();
  const latest = latestProposedBySymbol(proposed);
  const enterSymbols = latest.filter((row) => row.action === "ENTER").map((row) => row.symbol);
  const intended = new Set(latest.filter((row) => row.action === "ENTER" || row.action === "HOLD").map((row) => row.symbol));
  const heldSymbols = positions.map((row) => row.symbol.toUpperCase());

  if (!isTradingWeekdayUtc(now)) {
    alerts.push({
      severity: "info",
      message: "Weekend — automation is idle until Monday.",
      detail: "Crons only run Mon–Fri UTC. No action needed.",
    });
  }

  const latestFailed = jobRuns.find((run) => isFailureStatus(run.status));
  if (latestFailed && isTodayUtc(latestFailed.started_at ?? latestFailed.created_at)) {
    alerts.push({
      severity: "bad",
      message: `Latest failed job: ${friendlyJobName(latestFailed.job_name)}.`,
      detail: "Check Render logs for that cron or open Automation log below.",
    });
  }

  if (!health.enable_order_submission && (enterSymbols.length > 0 || latest.some((row) => row.action === "EXIT"))) {
    alerts.push({
      severity: "warn",
      message: "Bot has trade proposals but order submission is OFF.",
      detail: "Proposals will not become real orders until ENABLE_ORDER_SUBMISSION=true.",
    });
  }

  if (!health.trading_enabled) {
    alerts.push({
      severity: "warn",
      message: "Trading is disabled.",
      detail: "Set TRADING_ENABLED=true on trading crons.",
    });
  }

  const mismatchEvents = riskEvents.filter(
    (event) =>
      event.reason.toLowerCase().includes("unexpected_in_broker") ||
      event.reason.toLowerCase().includes("reconcile") ||
      event.reason.toLowerCase().includes("mismatch"),
  );
  if (mismatchEvents.length > 0) {
    alerts.push({
      severity: "warn",
      message: "Broker vs strategy mismatch detected.",
      detail: mismatchEvents[0]?.reason ?? "See Risk tab for details.",
    });
  } else {
    const orphanHeld = heldSymbols.filter((symbol) => latest.length > 0 && !intended.has(symbol));
    if (orphanHeld.length > 0) {
      alerts.push({
        severity: "warn",
        message: `Held but not in target portfolio: ${orphanHeld.join(", ")}.`,
        detail: "Strategy may propose EXIT on the next cycle, or reconcile will flag these.",
      });
    }
  }

  if (isTradingWeekdayUtc(now)) {
    const dayStart = startOfUtcDay(now);
    const weekdayRuns = jobRuns.filter((run) => {
      const at = parseIso(run.started_at ?? run.created_at);
      return at !== null && at >= dayStart && STRATEGY_JOB_NAMES.has(run.job_name);
    });
    const hourUtc = now.getUTCHours();
    if (hourUtc >= 16 && weekdayRuns.length === 0) {
      alerts.push({
        severity: "bad",
        message: "No strategy cycle has run yet today.",
        detail: "Check Render crons deployed and DATABASE_URL on each service.",
      });
    }
  }

  const todayOrders = orders.filter((order) => isTodayUtc(order.submitted_at ?? order.created_at));
  if (isTradingWeekdayUtc(now) && enterSymbols.length > 0 && todayOrders.length === 0 && health.enable_order_submission) {
    alerts.push({
      severity: "info",
      message: "ENTER proposals exist but no orders submitted yet today.",
      detail: "May be blocked by risk limits or waiting for the next execution cron.",
    });
  }

  if (
    isTradingWeekdayUtc(now) &&
    todayOrders.length === 0 &&
    enterSymbols.length === 0 &&
    latest.filter((row) => row.action === "EXIT").length === 0
  ) {
    alerts.push({
      severity: "info",
      message: "No trades today — rankings may be unchanged.",
      detail: "Normal on quiet days when the top ETF basket did not change.",
    });
  }

  if (!alerts.some((alert) => alert.severity === "bad" || alert.severity === "warn")) {
    alerts.push({
      severity: "ok",
      message: "Nothing alarming right now.",
      detail: "Check back after the next scheduled strategy cycle.",
    });
  }

  return alerts;
}

export function buildActivityTimeline(jobRuns: JobRun[], orders: Order[], limit = 20): ActivityItem[] {
  const items: ActivityItem[] = [];

  for (const run of jobRuns) {
    const at = parseIso(run.started_at ?? run.created_at);
    if (!at) {
      continue;
    }
    const ageMs = Date.now() - at.getTime();
    if (ageMs > 24 * 60 * 60 * 1000) {
      continue;
    }
    const status: StatusLevel = isSuccessStatus(run.status) ? "ok" : isFailureStatus(run.status) ? "bad" : "warn";
    items.push({
      at,
      kind: "job",
      status,
      message: `${friendlyJobName(run.job_name)} — ${run.status}`,
    });
  }

  for (const order of orders) {
    const at = parseIso(order.filled_at ?? order.submitted_at ?? order.created_at);
    if (!at) {
      continue;
    }
    const ageMs = Date.now() - at.getTime();
    if (ageMs > 24 * 60 * 60 * 1000) {
      continue;
    }
    const side = order.side.toUpperCase();
    const status: StatusLevel = order.status === "filled" ? "ok" : order.status === "rejected" ? "bad" : "warn";
    const pnlLabel = formatOrderPnl(order);
    const pnlSuffix = pnlLabel !== "—" ? ` · P&L ${pnlLabel}` : "";
    items.push({
      at,
      kind: "order",
      status,
      message: `${side} ${order.qty} ${order.symbol} — ${order.status}${pnlSuffix}`,
    });
  }

  return items.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, limit);
}

export function worstStatus(levels: StatusLevel[]): StatusLevel {
  if (levels.includes("bad")) {
    return "bad";
  }
  if (levels.includes("warn")) {
    return "warn";
  }
  return "ok";
}

export function buildGlanceSummary(
  alerts: Alert[],
  healthChecks: HealthCheck[],
  jobRuns: JobRun[],
  stats: TodayStats,
  account: AccountMetrics | null,
  nextCronLabel: string,
): GlanceSummary {
  const alertLevels = alerts
    .map((alert) => alert.severity)
    .filter((severity): severity is StatusLevel => severity !== "info");
  const overallStatus = worstStatus([...alertLevels, ...healthChecks.map((check) => check.status)]);
  const overallLabel =
    overallStatus === "ok" ? "All clear" : overallStatus === "warn" ? "Needs attention" : "Problem detected";

  const lastRun = jobRuns[0];
  const lastJobStatus: StatusLevel = lastRun
    ? isSuccessStatus(lastRun.status)
      ? "ok"
      : isFailureStatus(lastRun.status)
        ? "bad"
        : "warn"
    : "warn";

  const tradesSummary =
    stats.buysToday + stats.sellsToday > 0
      ? `${stats.buysToday} buy${stats.buysToday === 1 ? "" : "s"}, ${stats.sellsToday} sell${stats.sellsToday === 1 ? "" : "s"} today`
      : "No trades yet today";

  const pnl = account?.day_pnl;
  const pnlSummary =
    pnl === undefined
      ? "P&L unavailable"
      : `${pnl >= 0 ? "+" : ""}${pnl.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 })} today`;

  return {
    overallStatus,
    overallLabel,
    lastJobLabel: lastRun ? `${friendlyJobName(lastRun.job_name)} — ${lastRun.status}` : "No runs yet",
    lastJobRelative: lastRun ? formatRelativeTime(lastRun.started_at ?? lastRun.created_at) : "—",
    lastJobStatus,
    tradesSummary,
    pnlSummary,
    nextCronLabel,
  };
}
