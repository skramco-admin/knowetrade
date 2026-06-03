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

export function TickerList({ label, tickers, emptyLabel }: TickerListProps) {
  return (
    <article className="intent-block">
      <h4>{label}</h4>
      <p>{tickers.length > 0 ? tickers.join(", ") : emptyLabel}</p>
    </article>
  );
}
