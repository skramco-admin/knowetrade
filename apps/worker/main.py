from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from packages.alerts.slack import send_slack_alert
from packages.broker_alpaca.client import AlpacaBrokerClient, OrderRequest
from packages.core.risk import RiskConfig, can_place_order
from packages.core.strategy import Signal, generate_signals
from packages.db.helpers import (
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


def _symbols_from_env() -> list[str]:
    raw = os.getenv("TRADING_SYMBOLS", "SPY,QQQ,IVV")
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def run_once() -> None:
    init_database()
    started_at = datetime.now(timezone.utc)
    logger.info("job.start strategy_cycle")
    log_job_run(job_name="strategy_cycle", status="running", started_at=started_at)

    symbols = _symbols_from_env()
    signals: list[Signal] = generate_signals(symbols=symbols)
    broker = AlpacaBrokerClient()
    risk = RiskConfig(max_position_notional_usd=float(os.getenv("MAX_POSITION_NOTIONAL_USD", "10000")))

    for signal in signals:
        if signal.action != "BUY":
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
        order = broker.place_order(request)
        record_order_and_position(order_id=order["id"], symbol=signal.symbol, qty=signal.qty)

    log_job_run(job_name="strategy_cycle", status="success", started_at=started_at)
    logger.info("job.end strategy_cycle status=success")


def main() -> None:
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    while True:
        try:
            run_once()
        except Exception as exc:  # pragma: no cover - scaffold error path
            logger.exception("job.failed strategy_cycle")
            send_slack_alert(f"KnoweTrade worker failed: {exc}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
