export function parseIso(value?: string | null): Date | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value?: string | null): string {
  const date = parseIso(value);
  if (!date) {
    return value ? String(value) : "—";
  }
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatRelativeTime(value?: string | null): string {
  const date = parseIso(value);
  if (!date) {
    return "—";
  }
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 48) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function startOfUtcDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

export function isTodayUtc(value?: string | null): boolean {
  const date = parseIso(value);
  if (!date) {
    return false;
  }
  const now = new Date();
  return (
    date.getUTCFullYear() === now.getUTCFullYear() &&
    date.getUTCMonth() === now.getUTCMonth() &&
    date.getUTCDate() === now.getUTCDate()
  );
}

export function isTradingWeekdayUtc(date: Date = new Date()): boolean {
  const day = date.getUTCDay();
  return day >= 1 && day <= 5;
}

export function formatUsd(value: number | undefined): string {
  if (value === undefined) {
    return "—";
  }
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

export function formatPct(value: number | undefined): string {
  if (value === undefined) {
    return "—";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export function formatRealizedPnlUsd(value: number | undefined): string {
  if (value === undefined) {
    return "—";
  }
  const sign = value >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function formatRealizedPnlPct(value: number | undefined): string {
  if (value === undefined) {
    return "—";
  }
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function formatOrderPnl(order: {
  side: string;
  realized_pnl_usd?: number;
  realized_pnl_pct?: number;
}): string {
  if (order.side.toLowerCase() !== "sell") {
    return "—";
  }
  if (order.realized_pnl_usd === undefined || order.realized_pnl_pct === undefined) {
    return "—";
  }
  return `${formatRealizedPnlUsd(order.realized_pnl_usd)} (${formatRealizedPnlPct(order.realized_pnl_pct)})`;
}
