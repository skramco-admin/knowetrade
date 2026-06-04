from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from packages.core.trade_pnl import format_realized_pnl_pct, format_realized_pnl_usd

logger = logging.getLogger("knowetrade.alerts")


def is_trading_weekday_utc(now: datetime | None = None) -> bool:
    """Mon–Fri in UTC, aligned with Render cron schedules (1-5)."""
    moment = now or datetime.now(timezone.utc)
    return moment.weekday() < 5


def _alerts_enabled() -> bool:
    return os.getenv("SLACK_ALERTS_ENABLED", "true").strip().lower() == "true"


def _slack_trades_only() -> bool:
    mode = os.getenv("SLACK_NOTIFY_MODE", "trades_only").strip().lower().replace("-", "_")
    return mode in {"trades_only", "trade", "trades"}


def _post_to_slack(text: str, blocks: list[dict[str, Any]] | None = None) -> None:
    if not _alerts_enabled():
        logger.info("slack.disabled_via_flag message=%s", text)
        return

    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        logger.info("slack.disabled message=%s", text)
        return

    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        response = httpx.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
    except Exception:
        logger.exception("slack.send_failed")


def sendCriticalAlert(title: str, details: str) -> None:
    if _slack_trades_only():
        logger.info("slack.critical_suppressed title=%s details=%s", title, details)
        return
    text = f":rotating_light: *CRITICAL* - {title}\n{details}"
    _post_to_slack(text=text)


def sendWarningAlert(title: str, details: str) -> None:
    if _slack_trades_only():
        logger.info("slack.warning_suppressed title=%s details=%s", title, details)
        return
    text = f":warning: *WARNING* - {title}\n{details}"
    _post_to_slack(text=text)


def sendTradeAlert(
    *,
    symbol: str,
    side: str,
    qty: int,
    broker_order_id: str | None = None,
    fill_price: float | None = None,
    cost_basis: float | None = None,
    realized_pnl_usd: float | None = None,
    realized_pnl_pct: float | None = None,
) -> None:
    """Notify Slack when an order is submitted to the broker."""
    if not is_trading_weekday_utc():
        logger.info("slack.trade_skipped reason=non_trading_day symbol=%s side=%s", symbol, side)
        return
    order_ref = f" order_id={broker_order_id}" if broker_order_id else ""
    emoji = ":chart_with_upwards_trend:" if side.lower() == "buy" else ":chart_with_downwards_trend:"
    lines = [f"{emoji} *Trade executed* — {side.upper()} {qty} {symbol.upper()}{order_ref}"]
    if side.lower() == "sell" and fill_price is not None and fill_price > 0:
        lines.append(f"Sale ${fill_price:,.2f}/share")
        if cost_basis is not None and cost_basis > 0:
            lines.append(f"Cost ${cost_basis:,.2f}/share")
        if realized_pnl_usd is not None and realized_pnl_pct is not None:
            lines.append(f"P&L {format_realized_pnl_usd(realized_pnl_usd)} ({format_realized_pnl_pct(realized_pnl_pct)})")
    text = "\n".join(lines)
    _post_to_slack(text=text)


def sendDailySummary(summary_lines: list[str]) -> None:
    if _slack_trades_only():
        logger.info("slack.daily_summary_suppressed lines=%s", summary_lines)
        return
    if not is_trading_weekday_utc():
        logger.info("slack.daily_summary_skipped reason=non_trading_day")
        return
    if not summary_lines:
        summary_lines = ["No daily activity captured."]
    body = "\n".join(f"- {line}" for line in summary_lines)
    text = f":bar_chart: *Daily Summary*\n{body}"
    _post_to_slack(text=text)


def send_slack_alert(message: str) -> None:
    """Backwards-compatible generic alert helper."""
    _post_to_slack(text=message)
