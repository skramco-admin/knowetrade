const JOB_LABELS: Record<string, string> = {
  intraday_trading_workflow: "Strategy cycle",
  daily_postclose_workflow: "End-of-day rebalance",
  paper_order_execution: "Trade execution",
  daily_reconciliation: "Broker sync check",
  daily_summary: "Daily report",
  premarket_health_check: "Premarket health check",
  etf_data_ingestion: "Price data refresh",
  etf_signal_generation: "Signal generation",
  dry_run_portfolio_decisioning: "Portfolio decisions",
};

const JOB_DESCRIPTIONS: Record<string, string> = {
  intraday_trading_workflow: "Loads prices, ranks ETFs by momentum, decides trades, and may submit orders.",
  daily_postclose_workflow: "Final strategy pass after the US close — updates proposals before order-submit.",
  paper_order_execution: "Sends ENTER/EXIT proposals to Alpaca paper trading.",
  daily_reconciliation: "Compares broker holdings vs strategy intent and flags mismatches.",
  daily_summary: "End-of-day stats (Slack suppressed in trades-only mode).",
  premarket_health_check: "Checks database and broker connectivity before the session.",
  etf_data_ingestion: "Pulls latest daily bars from Alpaca.",
  etf_signal_generation: "Computes BUY/HOLD/EXIT trend signals.",
  dry_run_portfolio_decisioning: "Builds ENTER/HOLD/EXIT proposals from momentum rotation.",
};

export function friendlyJobName(jobName: string): string {
  return JOB_LABELS[jobName] ?? jobName.replace(/_/g, " ");
}

export function jobDescription(jobName: string): string {
  return JOB_DESCRIPTIONS[jobName] ?? "Automated background task.";
}

export const STRATEGY_JOB_NAMES = new Set([
  "intraday_trading_workflow",
  "daily_postclose_workflow",
]);

export const EXECUTION_JOB_NAMES = new Set(["paper_order_execution"]);
