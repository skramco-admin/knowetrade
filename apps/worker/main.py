from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from statistics import mean

from packages.alerts.slack import sendCriticalAlert, sendDailySummary, sendWarningAlert
from packages.broker_alpaca.client import (
    AlpacaBrokerClient,
    BrokerAuthError,
    OrderRejectedError,
    OrderRequest,
)
from packages.db.helpers import (
    get_setting_bool,
    init_database,
    list_active_etf_symbols,
    list_job_runs,
    list_latest_proposed_orders_for_symbols,
    list_latest_signals_for_symbols,
    list_recent_price_bars,
    record_broker_order,
    record_fill,
    log_job_run,
    record_proposed_order,
    record_signal,
    list_position_qty_by_symbols,
    upsert_price_bar,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("knowetrade.worker")


def _job_name() -> str:
    return os.getenv("WORKER_JOB_NAME", "etf_data_ingestion")


def _load_monitored_symbols() -> list[str]:
    strategy_bucket = os.getenv("STRATEGY_BUCKET", "etf_trend")
    symbols = list_active_etf_symbols(strategy_bucket=strategy_bucket)
    if not symbols:
        logger.warning("symbols.loaded asset_class=ETF strategy_bucket=%s active_count=0 tickers=", strategy_bucket)
        return symbols
    logger.info(
        "symbols.loaded asset_class=ETF strategy_bucket=%s active_count=%s tickers=%s",
        strategy_bucket,
        len(symbols),
        ",".join(symbols),
    )
    return symbols


def run_ingestion_job() -> None:
    run_once()


def run_signal_generation_job() -> None:
    run_once()


def run_dry_run_decisioning_job() -> None:
    run_once()


def run_paper_order_execution_job() -> None:
    run_once()


def run_premarket_health_check_job() -> None:
    run_once()


def run_reconciliation_job() -> None:
    run_once()


def run_daily_summary_job() -> None:
    run_once()


def run_postclose_workflow_job() -> None:
    run_once()


def _calculate_signal(closes: list[float]) -> tuple[str, float, str]:
    if len(closes) < 100:
        return "HOLD", 0.0, "insufficient_data_for_100d_ma"

    latest_close = closes[-1]
    sma20 = mean(closes[-20:])
    sma50 = mean(closes[-50:])
    sma100 = mean(closes[-100:])
    momentum20 = 0.0
    if len(closes) >= 21 and closes[-21] != 0:
        momentum20 = (latest_close / closes[-21]) - 1.0

    close_gt_50 = latest_close > sma50
    sma20_gt_50 = sma20 > sma50
    momentum_positive = momentum20 > 0

    if close_gt_50 and sma20_gt_50 and momentum_positive:
        signal = "BUY"
    elif (not close_gt_50) and (not sma20_gt_50) and momentum20 < 0:
        signal = "EXIT"
    else:
        signal = "HOLD"

    reason = (
        f"close={latest_close:.4f} sma20={sma20:.4f} sma50={sma50:.4f} "
        f"sma100={sma100:.4f} momentum20={momentum20:.6f}"
    )
    return signal, momentum20, reason


def _max_positions() -> int:
    return int(os.getenv("MAX_PORTFOLIO_POSITIONS", "5"))


def _max_open_positions() -> int:
    return int(os.getenv("MAX_OPEN_POSITIONS", str(_max_positions())))


def _max_position_pct() -> float:
    return float(os.getenv("MAX_POSITION_PCT", "0.20"))


def _app_mode() -> str:
    return os.getenv("APP_MODE", "paper").strip().lower()


def _trading_enabled() -> bool:
    return os.getenv("TRADING_ENABLED", "false").strip().lower() == "true"


def _order_submission_enabled() -> bool:
    env_value = os.getenv("ENABLE_ORDER_SUBMISSION")
    if env_value is not None:
        return env_value.strip().lower() == "true"
    return get_setting_bool("paper_order_submission_enabled", default=False)


def _paper_order_qty() -> int:
    return int(os.getenv("PAPER_ORDER_QTY", "1"))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def run_once() -> None:
    init_database()
    started_at = datetime.now(timezone.utc)
    job_name = _job_name()
    logger.info("job.start %s", job_name)

    symbols = _load_monitored_symbols()
    processed_count = len(symbols)
    succeeded_count = 0
    failed_count = 0
    processed_symbols: list[str] = []

    if job_name == "etf_signal_generation":
        for symbol in symbols:
            try:
                recent = list_recent_price_bars(symbol, limit=120)
                closes = [row["close"] for row in reversed(recent)]
                signal, strength, reason = _calculate_signal(closes)
                record_signal(symbol=symbol, signal_type=signal, strength=strength, reason=reason)
                logger.info("signal.generated symbol=%s signal=%s reason=%s", symbol, signal, reason)
                processed_symbols.append(symbol)
                succeeded_count += 1
            except Exception as exc:  # pragma: no cover - per-symbol safety
                failed_count += 1
                logger.exception("signal.generation_failed symbol=%s reason=%s", symbol, exc)

        status = "success" if failed_count == 0 else "completed_with_errors"
        sendDailySummary(
            [
                f"job={job_name}",
                f"symbols_processed={processed_count}",
                f"succeeded={succeeded_count}",
                f"failed={failed_count}",
                f"symbols_signaled_csv={','.join(processed_symbols)}",
            ]
        )
    elif job_name == "dry_run_portfolio_decisioning":
        latest_signals = list_latest_signals_for_symbols(symbols)
        signal_by_symbol = {row["symbol"]: row for row in latest_signals}
        considered_symbols = sorted(signal_by_symbol.keys())
        buy_candidates = sorted(
            [
                row
                for row in latest_signals
                if str(row["signal"]).upper() == "BUY"
            ],
            key=lambda row: (float(row["strength"]), row["symbol"]),
            reverse=True,
        )
        max_positions = _max_positions()
        target_symbols = [row["symbol"] for row in buy_candidates[:max_positions]]
        target_set = set(target_symbols)

        qty_by_symbol = list_position_qty_by_symbols(symbols)
        currently_held = {symbol for symbol, qty in qty_by_symbol.items() if qty > 0}

        entered = sorted(target_set - currently_held)
        held = sorted(target_set & currently_held)
        exited = sorted(currently_held - target_set)
        equal_weight = (1.0 / len(target_set)) if target_set else 0.0
        target_weight = min(equal_weight, _max_position_pct())

        for symbol in entered:
            row = signal_by_symbol.get(symbol, {})
            reason = f"enter_target equal_weight={target_weight:.4f}; {row.get('reason', '')}".strip()
            record_proposed_order(job_name, symbol, "ENTER", target_weight, reason)
            logger.info("decision.proposed symbol=%s action=ENTER reason=%s", symbol, reason)
        for symbol in held:
            row = signal_by_symbol.get(symbol, {})
            reason = f"hold_target equal_weight={target_weight:.4f}; {row.get('reason', '')}".strip()
            record_proposed_order(job_name, symbol, "HOLD", target_weight, reason)
            logger.info("decision.proposed symbol=%s action=HOLD reason=%s", symbol, reason)
        for symbol in exited:
            row = signal_by_symbol.get(symbol, {})
            reason = f"exit_target target_weight=0.0000; {row.get('reason', '')}".strip()
            record_proposed_order(job_name, symbol, "EXIT", 0.0, reason)
            logger.info("decision.proposed symbol=%s action=EXIT reason=%s", symbol, reason)

        succeeded_count = len(entered) + len(held) + len(exited)
        failed_count = 0
        status = "success"
        sendDailySummary(
            [
                f"job={job_name}",
                f"symbols_considered={len(considered_symbols)}",
                f"buy_candidates={','.join([row['symbol'] for row in buy_candidates])}",
                f"enters={','.join(entered)}",
                f"holds={','.join(held)}",
                f"exits={','.join(exited)}",
                f"target_weight={target_weight:.4f}",
            ]
        )
    elif job_name == "paper_order_execution":
        broker = AlpacaBrokerClient()
        latest_proposals = list_latest_proposed_orders_for_symbols(symbols)
        proposal_by_symbol = {row["symbol"]: row for row in latest_proposals}
        considered_symbols = sorted(proposal_by_symbol.keys())
        enter_symbols = sorted([s for s in considered_symbols if proposal_by_symbol[s]["action"] == "ENTER"])
        hold_symbols = sorted([s for s in considered_symbols if proposal_by_symbol[s]["action"] == "HOLD"])
        exit_symbols = sorted([s for s in considered_symbols if proposal_by_symbol[s]["action"] == "EXIT"])

        try:
            broker_positions = broker.list_positions()
        except BrokerAuthError as exc:
            sendCriticalAlert("Broker auth failure", str(exc))
            raise

        broker_qty_by_symbol = {position.symbol: position.qty for position in broker_positions if position.qty > 0}

        app_mode = _app_mode()
        trading_enabled = _trading_enabled()
        setting_enabled = _order_submission_enabled()
        submission_enabled = app_mode == "paper" and trading_enabled and setting_enabled
        max_open_positions = _max_open_positions()
        max_position_pct = _max_position_pct()
        submitted_count = 0
        rejected_count = 0
        order_qty = _paper_order_qty()

        if submission_enabled:
            broker.ensure_paper_trading()
            current_long_count = len([symbol for symbol, qty in broker_qty_by_symbol.items() if qty > 0])
            for symbol in enter_symbols:
                proposal = proposal_by_symbol.get(symbol, {})
                proposal_weight = float(proposal.get("target_weight", 0.0))
                if proposal_weight > max_position_pct:
                    logger.warning(
                        "order.skipped symbol=%s reason=max_position_pct_exceeded target_weight=%.4f max_position_pct=%.4f",
                        symbol,
                        proposal_weight,
                        max_position_pct,
                    )
                    continue
                if current_long_count >= max_open_positions:
                    logger.warning(
                        "order.skipped symbol=%s reason=max_open_positions_reached max_open_positions=%s",
                        symbol,
                        max_open_positions,
                    )
                    continue
                request = OrderRequest(symbol=symbol, qty=order_qty, side="buy")
                try:
                    order = broker.submit_paper_order(request)
                    local_order_id = record_broker_order(
                        broker_order_id=str(order.get("id", "")),
                        symbol=symbol,
                        qty=float(order.get("qty", order_qty)),
                        side=str(order.get("side", "buy")),
                        order_type=str(order.get("type", "market")),
                        status=str(order.get("status", "accepted")),
                        submitted_at=_parse_dt(order.get("submitted_at")),
                        filled_at=_parse_dt(order.get("filled_at")),
                    )
                    filled_qty = float(order.get("filled_qty") or 0)
                    filled_avg_price = float(order.get("filled_avg_price") or 0)
                    if filled_qty > 0 and filled_avg_price > 0:
                        record_fill(
                            order_id=local_order_id,
                            symbol=symbol,
                            fill_qty=filled_qty,
                            fill_price=filled_avg_price,
                            fill_time=_parse_dt(order.get("filled_at")),
                        )
                    submitted_count += 1
                    current_long_count += 1
                    sendWarningAlert(
                        "Order submitted",
                        f"symbol={symbol} side=buy qty={request.qty} broker_order_id={order.get('id')}",
                    )
                except OrderRejectedError as exc:
                    rejected_count += 1
                    sendWarningAlert("Order rejected", f"symbol={symbol} side=buy qty={request.qty} reason={exc}")
            for symbol in exit_symbols:
                qty = int(abs(broker_qty_by_symbol.get(symbol, 0)))
                if qty <= 0:
                    continue
                request = OrderRequest(symbol=symbol, qty=qty, side="sell")
                try:
                    order = broker.submit_paper_order(request)
                    local_order_id = record_broker_order(
                        broker_order_id=str(order.get("id", "")),
                        symbol=symbol,
                        qty=float(order.get("qty", qty)),
                        side=str(order.get("side", "sell")),
                        order_type=str(order.get("type", "market")),
                        status=str(order.get("status", "accepted")),
                        submitted_at=_parse_dt(order.get("submitted_at")),
                        filled_at=_parse_dt(order.get("filled_at")),
                    )
                    filled_qty = float(order.get("filled_qty") or 0)
                    filled_avg_price = float(order.get("filled_avg_price") or 0)
                    if filled_qty > 0 and filled_avg_price > 0:
                        record_fill(
                            order_id=local_order_id,
                            symbol=symbol,
                            fill_qty=filled_qty,
                            fill_price=filled_avg_price,
                            fill_time=_parse_dt(order.get("filled_at")),
                        )
                    submitted_count += 1
                    sendWarningAlert(
                        "Order submitted",
                        f"symbol={symbol} side=sell qty={request.qty} broker_order_id={order.get('id')}",
                    )
                except OrderRejectedError as exc:
                    rejected_count += 1
                    sendWarningAlert("Order rejected", f"symbol={symbol} side=sell qty={request.qty} reason={exc}")
        else:
            logger.info(
                "order.submission_disabled app_mode=%s trading_enabled=%s enable_order_submission=%s",
                app_mode,
                trading_enabled,
                setting_enabled,
            )

        intended_long_set = set(enter_symbols + hold_symbols)
        broker_long_set = {symbol for symbol, qty in broker_qty_by_symbol.items() if qty > 0}
        missing_in_broker = sorted(intended_long_set - broker_long_set)
        unexpected_in_broker = sorted(broker_long_set - intended_long_set)
        open_orders = broker.list_open_orders()
        broker_open_symbols = {order.symbol for order in open_orders}
        expected_open_symbols = set(enter_symbols + exit_symbols) if submission_enabled else set()
        missing_open_orders = sorted(expected_open_symbols - broker_open_symbols)
        unexpected_open_orders = sorted(broker_open_symbols - expected_open_symbols)
        if missing_in_broker or unexpected_in_broker:
            sendWarningAlert(
                "Reconcile mismatch",
                f"missing_in_broker={','.join(missing_in_broker)} unexpected_in_broker={','.join(unexpected_in_broker)}",
            )
            logger.warning(
                "reconcile.mismatch missing_in_broker=%s unexpected_in_broker=%s",
                ",".join(missing_in_broker),
                ",".join(unexpected_in_broker),
            )
        elif missing_open_orders or unexpected_open_orders:
            sendWarningAlert(
                "Reconcile mismatch",
                f"missing_open_orders={','.join(missing_open_orders)} unexpected_open_orders={','.join(unexpected_open_orders)}",
            )
            logger.warning(
                "reconcile.mismatch_open_orders missing_open_orders=%s unexpected_open_orders=%s",
                ",".join(missing_open_orders),
                ",".join(unexpected_open_orders),
            )
        else:
            logger.info("reconcile.match intended_vs_broker=true")

        succeeded_count = submitted_count
        failed_count = rejected_count
        processed_count = len(considered_symbols)
        status = "success" if rejected_count == 0 else "completed_with_errors"
        sendDailySummary(
            [
                f"job={job_name}",
                f"symbols_considered={len(considered_symbols)}",
                f"buy_candidates={','.join(enter_symbols)}",
                f"exits={','.join(exit_symbols)}",
                f"holds={','.join(hold_symbols)}",
                f"submitted={submitted_count}",
                f"rejected={rejected_count}",
                f"submission_enabled={submission_enabled}",
                f"app_mode={app_mode}",
                f"trading_enabled={trading_enabled}",
            ]
        )
    elif job_name == "premarket_health_check":
        broker = AlpacaBrokerClient()
        try:
            broker.validate_auth_strict()
            broker.ensure_paper_trading()
            succeeded_count = 1
            status = "success"
            sendDailySummary(
                [
                    f"job={job_name}",
                    "status=success",
                    f"symbols_loaded={processed_count}",
                    "broker_auth=ok",
                ]
            )
        except Exception as exc:
            failed_count = 1
            status = "failed"
            sendCriticalAlert("Premarket health check failure", str(exc))
    elif job_name == "daily_reconciliation":
        broker = AlpacaBrokerClient()
        latest_proposals = list_latest_proposed_orders_for_symbols(symbols)
        proposal_by_symbol = {row["symbol"]: row for row in latest_proposals}
        intended_long_set = {symbol for symbol, row in proposal_by_symbol.items() if row["action"] in {"ENTER", "HOLD"}}
        broker_positions = broker.list_positions()
        broker_long_set = {position.symbol for position in broker_positions if position.qty > 0}
        missing_in_broker = sorted(intended_long_set - broker_long_set)
        unexpected_in_broker = sorted(broker_long_set - intended_long_set)
        if missing_in_broker or unexpected_in_broker:
            failed_count = 1
            status = "completed_with_errors"
            sendWarningAlert(
                "Reconcile mismatch",
                f"missing_in_broker={','.join(missing_in_broker)} unexpected_in_broker={','.join(unexpected_in_broker)}",
            )
        else:
            status = "success"
            succeeded_count = len(intended_long_set)
            sendDailySummary(
                [
                    f"job={job_name}",
                    f"intended_positions={len(intended_long_set)}",
                    f"broker_positions={len(broker_long_set)}",
                    "status=success",
                ]
            )
    elif job_name == "daily_summary":
        recent_runs = list_job_runs(limit=25)
        status = "success"
        sendDailySummary(
            [
                f"job={job_name}",
                f"recent_runs={len(recent_runs)}",
                f"last_job={recent_runs[0]['job_name'] if recent_runs else 'none'}",
            ]
        )
    elif job_name == "daily_postclose_workflow":
        original_job = job_name
        try:
            os.environ["WORKER_JOB_NAME"] = "etf_data_ingestion"
            run_once()
            os.environ["WORKER_JOB_NAME"] = "etf_signal_generation"
            run_once()
            os.environ["WORKER_JOB_NAME"] = "dry_run_portfolio_decisioning"
            run_once()
            status = "success"
            succeeded_count = 3
        except Exception as exc:
            status = "failed"
            failed_count = 1
            sendCriticalAlert("Daily failure halt", f"postclose workflow halted: {exc}")
        finally:
            os.environ["WORKER_JOB_NAME"] = original_job
    else:
        broker = AlpacaBrokerClient()
        for symbol in symbols:
            try:
                bar = broker.get_latest_daily_bar(symbol)
                if bar is None:
                    failed_count += 1
                    logger.warning("bars.missing symbol=%s timeframe=1Day", symbol)
                    continue
                upsert_price_bar(
                    symbol=bar.symbol,
                    bar_time=bar.bar_time,
                    open_price=bar.open,
                    high_price=bar.high,
                    low_price=bar.low,
                    close_price=bar.close,
                    volume=bar.volume,
                    timeframe="1d",
                )
                logger.info(
                    "bars.ingested symbol=%s date=%s open=%.4f high=%.4f low=%.4f close=%.4f volume=%s",
                    bar.symbol,
                    bar.bar_time.date().isoformat(),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                )
                processed_symbols.append(bar.symbol)
                succeeded_count += 1
            except BrokerAuthError as exc:
                failed_count += 1
                logger.exception("bars.ingest_failed symbol=%s reason=%s", symbol, exc)
            except Exception as exc:  # pragma: no cover - safeguard for per-symbol errors
                failed_count += 1
                logger.exception("bars.ingest_failed symbol=%s reason=%s", symbol, exc)

        status = "success" if failed_count == 0 else "completed_with_errors"
        sendDailySummary(
            [
                f"job={job_name}",
                f"symbols_processed={processed_count}",
                f"succeeded={succeeded_count}",
                f"failed={failed_count}",
                f"symbols_ingested_csv={','.join(processed_symbols)}",
            ]
        )

    log_job_run(job_name=job_name, status=status, started_at=started_at)
    logger.info(
        "job.end %s status=%s symbols_processed=%s succeeded=%s failed=%s",
        job_name,
        status,
        processed_count,
        succeeded_count,
        failed_count,
    )


def main() -> None:
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    while True:
        try:
            run_once()
        except Exception as exc:  # pragma: no cover - scaffold error path
            logger.exception("job.failed %s", _job_name())
            sendCriticalAlert("Job failure", f"KnoweTrade worker failed: {exc}")
        time.sleep(poll_seconds)


def main_once() -> None:
    try:
        run_once()
    except Exception as exc:  # pragma: no cover - scaffold error path
        logger.exception("job.failed %s", _job_name())
        sendCriticalAlert("Job failure", f"KnoweTrade worker failed: {exc}")
        raise


if __name__ == "__main__":
    main()
