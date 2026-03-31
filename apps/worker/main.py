from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from packages.alerts.slack import sendCriticalAlert, sendDailySummary, sendWarningAlert
from packages.broker_alpaca.client import (
    AlpacaBrokerClient,
    BrokerAuthError,
    OrderRejectedError,
    OrderRequest,
)
from packages.core.risk import RiskConfig, can_place_order
from packages.core.strategy import Signal, generate_signals
from packages.db.helpers import (
    get_position_qty,
    init_database,
    log_job_run,
    record_order_and_position,
    record_risk_event,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("knowetrade.worker")
_last_summary_sent_at: datetime | None = None


def _symbols_from_env() -> list[str]:
    raw = os.getenv("TRADING_SYMBOLS", "SPY,QQQ,IVV")
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _check_daily_loss_threshold() -> None:
    """Placeholder breach detector until PnL snapshots are fully wired."""
    daily_pnl_pct = float(os.getenv("DAILY_PNL_PCT", "0"))
    loss_threshold_pct = float(os.getenv("DAILY_LOSS_THRESHOLD_PCT", "-2.0"))
    if daily_pnl_pct <= loss_threshold_pct:
        sendCriticalAlert(
            "Daily loss threshold breached",
            f"daily_pnl_pct={daily_pnl_pct} threshold={loss_threshold_pct}",
        )


def _target_position_qty_per_symbol() -> float:
    return float(os.getenv("TARGET_POSITION_QTY_PER_SYMBOL", "1"))


def _should_send_summary(now: datetime) -> bool:
    global _last_summary_sent_at
    interval_minutes = int(os.getenv("SUMMARY_INTERVAL_MINUTES", "1440"))
    if interval_minutes <= 0:
        _last_summary_sent_at = now
        return True
    if _last_summary_sent_at is None:
        _last_summary_sent_at = now
        return True
    elapsed_seconds = (now - _last_summary_sent_at).total_seconds()
    if elapsed_seconds >= interval_minutes * 60:
        _last_summary_sent_at = now
        return True
    return False


def run_once() -> None:
    init_database()
    started_at = datetime.now(timezone.utc)
    logger.info("job.start strategy_cycle")
    log_job_run(job_name="strategy_cycle", status="running", started_at=started_at)

    symbols = _symbols_from_env()
    signals: list[Signal] = generate_signals(symbols=symbols)
    broker = AlpacaBrokerClient()
    risk = RiskConfig(max_position_notional_usd=float(os.getenv("MAX_POSITION_NOTIONAL_USD", "10000")))
    placed_orders = 0
    order_rejections = 0
    target_qty = _target_position_qty_per_symbol()

    try:
        broker.validate_auth()
    except BrokerAuthError as exc:
        sendCriticalAlert("Broker auth failure", str(exc))
        raise

    for signal in signals:
        if signal.action != "BUY":
            continue

        current_qty = get_position_qty(signal.symbol)
        if current_qty >= target_qty:
            logger.info(
                "position.target_reached symbol=%s current_qty=%.4f target_qty=%.4f",
                signal.symbol,
                current_qty,
                target_qty,
            )
            continue

        allowed, reason = can_place_order(
            symbol=signal.symbol,
            side="BUY",
            qty=signal.qty,
            price=signal.reference_price,
            risk_config=risk,
        )
        if not allowed:
            logger.warning("risk.blocked symbol=%s reason=%s", signal.symbol, reason)
            record_risk_event(signal.symbol, reason)
            continue

        request = OrderRequest(symbol=signal.symbol, qty=signal.qty, side="buy")
        logger.info("broker.call place_order symbol=%s qty=%s", request.symbol, request.qty)
        try:
            order = broker.place_order(request)
            record_order_and_position(order_id=order["id"], symbol=signal.symbol, qty=signal.qty)
            placed_orders += 1
        except OrderRejectedError as exc:
            order_rejections += 1
            record_risk_event(signal.symbol, f"order_rejected: {exc}")
            sendWarningAlert(
                "Order rejection",
                f"symbol={signal.symbol} qty={signal.qty} reason={exc}",
            )
        except BrokerAuthError as exc:
            sendCriticalAlert("Broker auth failure", f"during order placement: {exc}")
            raise

    # Placeholder reconciliation check until full reconcile module exists.
    force_mismatch = os.getenv("RECONCILE_FORCE_MISMATCH", "false").lower() == "true"
    if force_mismatch:
        sendWarningAlert(
            "Reconcile mismatch",
            "Forced mismatch detected via RECONCILE_FORCE_MISMATCH=true",
        )

    _check_daily_loss_threshold()

    if _should_send_summary(now=datetime.now(timezone.utc)):
        sendDailySummary(
            [
                f"job=strategy_cycle",
                f"symbols={len(symbols)}",
                f"signals={len(signals)}",
                f"placed_orders={placed_orders}",
                f"order_rejections={order_rejections}",
            ]
        )

    log_job_run(job_name="strategy_cycle", status="success", started_at=started_at)
    logger.info("job.end strategy_cycle status=success")


def main() -> None:
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    while True:
        try:
            run_once()
        except Exception as exc:  # pragma: no cover - scaffold error path
            logger.exception("job.failed strategy_cycle")
            sendCriticalAlert("Job failure", f"KnoweTrade worker failed: {exc}")
        time.sleep(poll_seconds)


def main_once() -> None:
    try:
        run_once()
    except Exception as exc:  # pragma: no cover - scaffold error path
        logger.exception("job.failed strategy_cycle")
        sendCriticalAlert("Job failure", f"KnoweTrade worker failed: {exc}")
        raise


if __name__ == "__main__":
    main()
