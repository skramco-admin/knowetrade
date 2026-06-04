import type { StatusLevel, AlertSeverity } from "../dashboardInsights";

type StatusPillProps = {
  status: StatusLevel;
  label: string;
};

export function StatusPill({ status, label }: StatusPillProps) {
  return <span className={`status-pill status-${status}`}>{label}</span>;
}

type AlertListProps = {
  items: { severity: AlertSeverity; message: string; detail?: string }[];
};

export function AlertList({ items }: AlertListProps) {
  return (
    <ul className="alert-list">
      {items.map((item, index) => (
        <li key={`${item.message}-${index}`} className={`alert-item alert-${item.severity}`}>
          <strong>{item.message}</strong>
          {item.detail ? <span>{item.detail}</span> : null}
        </li>
      ))}
    </ul>
  );
}

type HealthCheckListProps = {
  checks: { id: string; label: string; status: StatusLevel; message: string; fixHint?: string }[];
};

export function HealthCheckList({ checks }: HealthCheckListProps) {
  return (
    <ul className="health-list">
      {checks.map((check) => (
        <li key={check.id} className={`health-item health-${check.status}`}>
          <div className="health-item-head">
            <StatusPill status={check.status} label={check.status === "ok" ? "OK" : check.status === "warn" ? "Check" : "Fix"} />
            <strong>{check.label}</strong>
          </div>
          <p>{check.message}</p>
          {check.fixHint ? <p className="health-fix">What to do: {check.fixHint}</p> : null}
        </li>
      ))}
    </ul>
  );
}

type ActivityTimelineProps = {
  items: { at: Date; kind: "job" | "order"; status: StatusLevel; message: string }[];
};

export function ActivityTimeline({ items }: ActivityTimelineProps) {
  if (items.length === 0) {
    return <p className="muted">No activity in the last 24 hours.</p>;
  }

  return (
    <ul className="timeline">
      {items.map((item, index) => (
        <li key={`${item.kind}-${item.at.toISOString()}-${index}`} className={`timeline-item timeline-${item.status}`}>
          <time>{item.at.toLocaleString()}</time>
          <span>{item.message}</span>
        </li>
      ))}
    </ul>
  );
}

type TickerListProps = {
  label: string;
  tickers: string[];
  emptyLabel: string;
};

type AccountOverviewPanelProps = {
  overview: {
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
  formatUsd: (value: number | undefined) => string;
  formatPct: (value: number | undefined) => string;
};

export function AccountOverviewPanel({ overview, formatUsd, formatPct }: AccountOverviewPanelProps) {
  return (
    <div className="account-overview">
      <div className="account-hero">
        <div>
          <p className="account-hero-label">Total paper trading account</p>
          <p className="account-hero-value">{formatUsd(overview.totalValue)}</p>
          <p className="muted">
            Alpaca paper account · started at {formatUsd(overview.startingEquity)}
          </p>
        </div>
        <StatusPill status={overview.overallStatus} label={overview.overallLabel} />
      </div>
      <div className="account-grid">
        <article className="account-stat">
          <h3>All-time gain / loss</h3>
          <p className={overview.lifetimePnl < 0 ? "pnl-negative" : "pnl-positive"}>
            {formatUsd(overview.lifetimePnl)} ({formatPct(overview.lifetimePnlPct)})
          </p>
          <p className="muted">Vs your paper starting balance</p>
        </article>
        <article className="account-stat">
          <h3>{overview.dayLabel}</h3>
          <p className={overview.dayPnl < 0 ? "pnl-negative" : "pnl-positive"}>
            {formatUsd(overview.dayPnl)} ({formatPct(overview.dayPnlPct)})
          </p>
          <p className="muted">Since yesterday&apos;s close</p>
        </article>
        <article className="account-stat">
          <h3>Cash</h3>
          <p>{formatUsd(overview.cash)}</p>
        </article>
        <article className="account-stat">
          <h3>In the market (ETFs)</h3>
          <p>{formatUsd(overview.inMarket)}</p>
        </article>
        <article className="account-stat">
          <h3>Open positions</h3>
          <p>{overview.openPositions}</p>
        </article>
        <article className="account-stat">
          <h3>Realized P&amp;L (tracked sells)</h3>
          <p className={overview.realizedPnlTracked < 0 ? "pnl-negative" : "pnl-positive"}>
            {formatUsd(overview.realizedPnlTracked)}
          </p>
          <p className="muted">Sum of closed trades recorded by KnoweTrade</p>
        </article>
      </div>
    </div>
  );
}

export function TickerList({ label, tickers, emptyLabel }: TickerListProps) {
  return (
    <article className="intent-block">
      <h4>{label}</h4>
      <p>{tickers.length > 0 ? tickers.join(", ") : emptyLabel}</p>
    </article>
  );
}
