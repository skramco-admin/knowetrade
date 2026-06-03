import { useEffect, useMemo, useState } from "react";
import {
  getAccountMetrics,
  getJobRuns,
  getOrders,
  getPositions,
  getProposedOrders,
  getRiskEvents,
  getSystemHealth,
  type AccountMetrics,
} from "../api";
import { ActivityTimeline, AlertList, HealthCheckList, StatusPill, TickerList } from "../components/OperatorUi";
import {
  buildActivityTimeline,
  buildAlerts,
  buildGlanceSummary,
  buildHealthChecks,
  buildPortfolioIntent,
  buildTodayStats,
} from "../dashboardInsights";
import { formatPct, formatUsd } from "../format";
import { getTradingCronCountdowns, type CronCountdown } from "../schedule";

export function DashboardPage() {
  const [account, setAccount] = useState<AccountMetrics | null>(null);
  const [cronCountdowns, setCronCountdowns] = useState<CronCountdown[]>(getTradingCronCountdowns());
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [jobRuns, setJobRuns] = useState<Awaited<ReturnType<typeof getJobRuns>>>([]);
  const [orders, setOrders] = useState<Awaited<ReturnType<typeof getOrders>>>([]);
  const [proposed, setProposed] = useState<Awaited<ReturnType<typeof getProposedOrders>>>([]);
  const [positions, setPositions] = useState<Awaited<ReturnType<typeof getPositions>>>([]);
  const [riskEvents, setRiskEvents] = useState<Awaited<ReturnType<typeof getRiskEvents>>>([]);
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getSystemHealth>> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [healthData, runs, orderRows, proposedRows, positionRows, riskRows, accountData] = await Promise.all([
          getSystemHealth(),
          getJobRuns(),
          getOrders(),
          getProposedOrders(),
          getPositions(),
          getRiskEvents(),
          getAccountMetrics(),
        ]);
        if (cancelled) {
          return;
        }
        setHealth(healthData);
        setJobRuns(runs);
        setOrders(orderRows);
        setProposed(proposedRows);
        setPositions(positionRows);
        setRiskEvents(riskRows);
        setAccount(accountData);
        setError("");
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load().catch(() => undefined);
    const refreshTimer = window.setInterval(() => {
      load().catch(() => undefined);
    }, 60_000);
    const countdownTimer = window.setInterval(() => {
      setCronCountdowns(getTradingCronCountdowns());
    }, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(refreshTimer);
      window.clearInterval(countdownTimer);
    };
  }, []);

  const nextCron = cronCountdowns[0];
  const portfolio = useMemo(() => buildPortfolioIntent(proposed), [proposed]);
  const todayStats = useMemo(() => buildTodayStats(jobRuns, proposed, orders), [jobRuns, proposed, orders]);
  const healthChecks = useMemo(
    () => (health ? buildHealthChecks(health, jobRuns) : []),
    [health, jobRuns],
  );
  const alerts = useMemo(
    () => (health ? buildAlerts(health, jobRuns, proposed, orders, riskEvents, positions) : []),
    [health, jobRuns, proposed, orders, riskEvents, positions],
  );
  const timeline = useMemo(() => buildActivityTimeline(jobRuns, orders), [jobRuns, orders]);
  const glance = useMemo(
    () =>
      buildGlanceSummary(
        alerts,
        healthChecks,
        jobRuns,
        todayStats,
        account,
        nextCron ? `${nextCron.label} in ${nextCron.countdown}` : "—",
      ),
    [alerts, healthChecks, jobRuns, todayStats, account, nextCron],
  );

  const pnl = account?.day_pnl;
  const pnlLabel = pnl === undefined ? "Today" : pnl >= 0 ? "Up today" : "Down today";

  return (
    <section className="dashboard">
      <div className="card glance-card">
        <div className="glance-head">
          <div>
            <h2>Today at a glance</h2>
            <p className="muted">Plain-English status — refresh every 60 seconds.</p>
          </div>
          <StatusPill status={glance.overallStatus} label={glance.overallLabel} />
        </div>
        {loading ? <p className="muted">Loading dashboard…</p> : null}
        {error ? <p role="alert" className="error">API error: {error}</p> : null}
        <div className="glance-grid">
          <article className="glance-item">
            <h3>Latest automation</h3>
            <p>
              <StatusPill status={glance.lastJobStatus} label={glance.lastJobStatus === "ok" ? "OK" : glance.lastJobStatus === "warn" ? "Check" : "Fix"} />{" "}
              {glance.lastJobLabel}
            </p>
            <p className="muted">{glance.lastJobRelative}</p>
          </article>
          <article className="glance-item">
            <h3>Trades today</h3>
            <p>{glance.tradesSummary}</p>
          </article>
          <article className="glance-item">
            <h3>{pnlLabel}</h3>
            <p>
              {formatUsd(account?.day_pnl)} ({formatPct(account?.day_pnl_pct)})
            </p>
          </article>
          <article className="glance-item">
            <h3>Next scheduled check</h3>
            <p>{nextCron?.label ?? "—"}</p>
            <p className="muted">
              in {nextCron?.countdown ?? "—"} · local {nextCron?.nextRunLocal ?? "—"}
            </p>
          </article>
        </div>
      </div>

      <div className="card">
        <h2>When to worry</h2>
        <AlertList items={alerts} />
      </div>

      <div className="card">
        <h2>Is it working?</h2>
        <HealthCheckList checks={healthChecks} />
      </div>

      <div className="card">
        <h2>Did anything happen today?</h2>
        <div className="grid">
          <article className="metric">
            <h3>Strategy cycles OK</h3>
            <p>{todayStats.strategyCyclesSucceeded}</p>
          </article>
          <article className="metric">
            <h3>Strategy cycles failed</h3>
            <p>{todayStats.strategyCyclesFailed}</p>
          </article>
          <article className="metric">
            <h3>Trade execution runs OK</h3>
            <p>{todayStats.executionRunsSucceeded}</p>
          </article>
          <article className="metric">
            <h3>Proposals: ENTER / EXIT / HOLD</h3>
            <p>
              {todayStats.enterCount} / {todayStats.exitCount} / {todayStats.holdCount}
            </p>
          </article>
          <article className="metric">
            <h3>Orders submitted</h3>
            <p>{todayStats.ordersSubmitted}</p>
          </article>
          <article className="metric">
            <h3>Orders filled</h3>
            <p>{todayStats.ordersFilled}</p>
          </article>
        </div>
      </div>

      <div className="card">
        <h2>What the bot wants to hold</h2>
        <p className="muted">From the latest momentum rotation proposals (top-ranked ETFs).</p>
        <div className="intent-grid">
          <TickerList label="Holding (target)" tickers={portfolio.holding} emptyLabel="None in target portfolio yet." />
          <TickerList label="Want to buy (ENTER)" tickers={portfolio.wantToBuy} emptyLabel="No new buys proposed." />
          <TickerList label="Want to sell (EXIT)" tickers={portfolio.wantToSell} emptyLabel="No sells proposed." />
        </div>
      </div>

      <div className="card">
        <h2>Last 24 hours</h2>
        <ActivityTimeline items={timeline} />
      </div>

      <div className="card">
        <h2>Portfolio snapshot</h2>
        <div className="grid">
          <article className="metric">
            <h3>Active positions</h3>
            <p>{positions.length}</p>
          </article>
          <article className="metric">
            <h3>Portfolio equity</h3>
            <p>{formatUsd(account?.equity)}</p>
          </article>
          <article className="metric">
            <h3>Cash</h3>
            <p>{formatUsd(account?.cash)}</p>
          </article>
          <article className="metric">
            <h3>Buying power</h3>
            <p>{formatUsd(account?.buying_power)}</p>
          </article>
        </div>
      </div>

      <div className="card">
        <h2>Full schedule (Mon–Fri UTC)</h2>
        <ul className="list">
          {cronCountdowns.map((item) => (
            <li key={item.label}>
              <strong>{item.label}:</strong> in {item.countdown} (local: {item.nextRunLocal})
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
