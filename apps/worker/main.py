from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Callable

from packages.alerts.slack import (
    is_trading_weekday_utc,
    sendCriticalAlert,
    sendDailySummary,
    sendTradeAlert,
    sendWarningAlert,
)
from packages.core.position_sizing import compute_target_buy_qty, normalize_order_sizing_mode
from packages.core.risk import resolve_risk_limits
from packages.core.rotation import (
    build_rotation_decision,
    rank_symbols_by_momentum,
    rotation_reason,
)
from packages.core.signals import calculate_trend_signal, rules_for_appetite
from packages.core.trade_pnl import compute_realized_sell_pnl
from packages.broker_alpaca.client import (
    AlpacaBrokerClient,
    BrokerAuthError,
    OrderRejectedError,
    OrderRequest,
)
from packages.db.helpers import (
    get_position_avg_price,
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
    record_risk_event,
    record_signal,
    list_position_qty_by_symbols,
    upsert_price_bar,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("knowetrade.worker")

_SCHEDULED_TRADING_JOBS = frozenset(
    {
        "daily_summary",
        "premarket_health_check",
        "daily_postclose_workflow",
        "intraday_trading_workflow",
        "paper_order_execution",
        "daily_reconciliation",
        "etf_data_ingestion",
        "etf_signal_generation",
        "dry_run_portfolio_decisioning",
    }
)


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
    main_once()


def run_postclose_workflow_job() -> None:
    run_once()


def run_intraday_trading_workflow_job() -> None:
    main_once()


def _risk_appetite() -> str:
    from packages.core.risk import normalize_risk_appetite

    return normalize_risk_appetite(os.getenv("RISK_APPETITE"))


def _signal_rules():
    return rules_for_appetite(_risk_appetite())


def _risk_limits():
    return resolve_risk_limits(_risk_appetite())


def _run_trading_pipeline_steps(*, include_order_execution: bool) -> tuple[str, int, int]:
    original_job = _job_name()
    try:
        os.environ["WORKER_JOB_NAME"] = "etf_data_ingestion"
        run_once()
        os.environ["WORKER_JOB_NAME"] = "etf_signal_generation"
        run_once()
        os.environ["WORKER_JOB_NAME"] = "dry_run_portfolio_decisioning"
        run_once()
        succeeded_count = 3
        if include_order_execution:
            os.environ["WORKER_JOB_NAME"] = "paper_order_execution"
            run_once()
            succeeded_count = 4
        return "success", succeeded_count, 0
    finally:
        os.environ["WORKER_JOB_NAME"] = original_job


def _calculate_signal(closes: list[float]) -> tuple[str, float, str]:
    return calculate_trend_signal(closes, _signal_rules())


def _max_positions() -> int:
    return _risk_limits().max_portfolio_positions


def _max_open_positions() -> int:
    return _risk_limits().max_open_positions


def _max_position_pct() -> float:
    return _risk_limits().max_position_pct


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
    return _risk_limits().paper_order_qty


def _order_sizing_mode() -> str:
    return normalize_order_sizing_mode(os.getenv("ORDER_SIZING_MODE"))


def _resolve_reference_price(broker: AlpacaBrokerClient, symbol: str) -> float | None:
    try:
        bar = broker.get_latest_daily_bar(symbol)
        if bar is not None and bar.close > 0:
            return float(bar.close)
    except Exception as exc:
        logger.warning("order.price_lookup_failed symbol=%s reason=%s", symbol, exc)
    return None


def _resolve_buy_qty(
    *,
    broker: AlpacaBrokerClient,
    symbol: str,
    proposal_weight: float,
    current_qty: float,
    equity: float,
    cash: float,
) -> int | None:
    limits = _risk_limits()
    if _order_sizing_mode() == "fixed_qty":
        return _paper_order_qty()

    price = _resolve_reference_price(broker, symbol)
    if price is None:
        logger.warning("order.skipped symbol=%s reason=missing_reference_price", symbol)
        return None

    qty = compute_target_buy_qty(
        equity=equity,
        cash=cash,
        target_weight=proposal_weight,
        price=price,
        current_qty=current_qty,
        max_position_pct=limits.max_position_pct,
        max_position_notional_usd=limits.max_position_notional_usd,
    )
    if qty < 1:
        logger.info(
            "order.skipped symbol=%s reason=zero_target_qty equity=%.2f target_weight=%.4f price=%.4f current_qty=%.4f cash=%.2f",
            symbol,
            equity,
            proposal_weight,
            price,
            current_qty,
            cash,
        )
        return None

    logger.info(
        "order.sized symbol=%s mode=%s equity=%.2f target_weight=%.4f price=%.4f current_qty=%.4f qty=%s notional=%.2f",
        symbol,
        _order_sizing_mode(),
        equity,
        proposal_weight,
        price,
        current_qty,
        qty,
        qty * price,
    )
    return qty


def _portfolio_strategy() -> str:
    return os.getenv("PORTFOLIO_STRATEGY", "momentum_rotation").strip().lower().replace("-", "_")


def _momentum_lookback_days() -> int:
    return int(os.getenv("MOMENTUM_LOOKBACK_DAYS", "20"))


def _load_symbol_closes(symbols: list[str], *, limit: int = 120) -> dict[str, list[float]]:
    closes_by_symbol: dict[str, list[float]] = {}
    for symbol in symbols:
        recent = list_recent_price_bars(symbol, limit=limit)
        if not recent:
            continue
        closes_by_symbol[symbol.upper()] = [row["close"] for row in reversed(recent)]
    return closes_by_symbol


def _apply_portfolio_proposals(
    *,
    job_name: str,
    entered: tuple[str, ...] | list[str],
    held: tuple[str, ...] | list[str],
    exited: tuple[str, ...] | list[str],
    target_weight: float,
    reason_for_symbol: Callable[[str, str], str],
) -> None:
    for symbol in entered:
        reason = reason_for_symbol("ENTER", symbol)
        record_proposed_order(job_name, symbol, "ENTER", target_weight, reason)
        logger.info("decision.proposed symbol=%s action=ENTER reason=%s", symbol, reason)
    for symbol in held:
        reason = reason_for_symbol("HOLD", symbol)
        record_proposed_order(job_name, symbol, "HOLD", target_weight, reason)
        logger.info("decision.proposed symbol=%s action=HOLD reason=%s", symbol, reason)
    for symbol in exited:
        reason = reason_for_symbol("EXIT", symbol)
        record_proposed_order(job_name, symbol, "EXIT", 0.0, reason)
        logger.info("decision.proposed symbol=%s action=EXIT reason=%s", symbol, reason)


def _run_momentum_rotation_decisioning(symbols: list[str], job_name: str) -> dict[str, object]:
    closes_by_symbol = _load_symbol_closes(symbols)
    ranked = rank_symbols_by_momentum(closes_by_symbol, lookback=_momentum_lookback_days())
    rank_by_symbol = {row.symbol: index + 1 for index, row in enumerate(ranked)}
    momentum_by_symbol = {row.symbol: row.momentum for row in ranked}

    broker = AlpacaBrokerClient()
    currently_held = _held_symbols_for_decisions(symbols, broker=broker)
    decision = build_rotation_decision(
        ranked=ranked,
        currently_held=currently_held,
        max_positions=_max_positions(),
        max_position_pct=_max_position_pct(),
    )

    def reason_for(action: str, symbol: str) -> str:
        upper = symbol.upper()
        return rotation_reason(
            action=action,
            symbol=upper,
            rank=rank_by_symbol.get(upper),
            momentum=momentum_by_symbol.get(upper),
            target_weight=decision.target_weight,
        )

    _apply_portfolio_proposals(
        job_name=job_name,
        entered=decision.entered,
        held=decision.held,
        exited=decision.exited,
        target_weight=decision.target_weight,
        reason_for_symbol=reason_for,
    )
    top_symbols = [row.symbol for row in decision.ranked]
    return {
        "considered_count": len(closes_by_symbol),
        "ranked_count": len(ranked),
        "top_targets": top_symbols,
        "entered": list(decision.entered),
        "held": list(decision.held),
        "exited": list(decision.exited),
        "target_weight": decision.target_weight,
    }


def _run_trend_following_decisioning(symbols: list[str], job_name: str) -> dict[str, object]:
    latest_signals = list_latest_signals_for_symbols(symbols)
    signal_by_symbol = {row["symbol"]: row for row in latest_signals}
    buy_candidates = sorted(
        [row for row in latest_signals if str(row["signal"]).upper() == "BUY"],
        key=lambda row: (float(row["strength"]), row["symbol"]),
        reverse=True,
    )
    max_positions = _max_positions()
    target_set = {row["symbol"] for row in buy_candidates[:max_positions]}

    broker = AlpacaBrokerClient()
    currently_held = _held_symbols_for_decisions(symbols, broker=broker)
    entered = sorted(target_set - currently_held)
    held = sorted(target_set & currently_held)
    exited = sorted(currently_held - target_set)
    equal_weight = (1.0 / len(target_set)) if target_set else 0.0
    target_weight = min(equal_weight, _max_position_pct())

    def reason_for(action: str, symbol: str) -> str:
        row = signal_by_symbol.get(symbol, {})
        if action == "EXIT":
            return f"exit_target target_weight=0.0000; {row.get('reason', '')}".strip()
        prefix = "enter_target" if action == "ENTER" else "hold_target"
        return f"{prefix} equal_weight={target_weight:.4f}; {row.get('reason', '')}".strip()

    _apply_portfolio_proposals(
        job_name=job_name,
        entered=entered,
        held=held,
        exited=exited,
        target_weight=target_weight,
        reason_for_symbol=reason_for,
    )
    return {
        "considered_count": len(signal_by_symbol),
        "ranked_count": len(buy_candidates),
        "top_targets": [row["symbol"] for row in buy_candidates[:max_positions]],
        "entered": entered,
        "held": held,
        "exited": exited,
        "target_weight": target_weight,
    }


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _auto_exit_orphan_positions() -> bool:
    return os.getenv("AUTO_EXIT_ORPHAN_POSITIONS", "true").strip().lower() == "true"


def _monitored_symbol_set(symbols: list[str]) -> set[str]:
    return {symbol.upper() for symbol in symbols}


def _local_long_symbols(symbols: list[str]) -> set[str]:
    qty_by_symbol = list_position_qty_by_symbols(symbols)
    return {symbol for symbol, qty in qty_by_symbol.items() if qty > 0}


def _broker_long_symbols(broker: AlpacaBrokerClient, monitored: set[str]) -> set[str]:
    broker_positions = broker.list_positions()
    return {
        position.symbol.upper()
        for position in broker_positions
        if position.qty > 0 and position.symbol.upper() in monitored
    }


def _record_reconcile_mismatch(
    *,
    job_name: str,
    missing_in_broker: list[str],
    unexpected_in_broker: list[str],
    missing_open_orders: list[str] | None = None,
    unexpected_open_orders: list[str] | None = None,
) -> None:
    missing_open_orders = missing_open_orders or []
    unexpected_open_orders = unexpected_open_orders or []
    if not (missing_in_broker or unexpected_in_broker or missing_open_orders or unexpected_open_orders):
        return

    parts: list[str] = []
    if missing_in_broker:
        parts.append(f"missing at broker: {', '.join(missing_in_broker)}")
    if unexpected_in_broker:
        parts.append(f"unexpected at broker: {', '.join(unexpected_in_broker)}")
    if missing_open_orders:
        parts.append(f"missing open orders: {', '.join(missing_open_orders)}")
    if unexpected_open_orders:
        parts.append(f"unexpected open orders: {', '.join(unexpected_open_orders)}")

    symbol = None
    if len(unexpected_in_broker) == 1:
        symbol = unexpected_in_broker[0]
    elif len(missing_in_broker) == 1:
        symbol = missing_in_broker[0]

    record_risk_event(
        f"Reconcile mismatch — {'; '.join(parts)}",
        symbol=symbol,
        severity="warning",
        details={
            "job": job_name,
            "missing_in_broker": missing_in_broker,
            "unexpected_in_broker": unexpected_in_broker,
            "missing_open_orders": missing_open_orders,
            "unexpected_open_orders": unexpected_open_orders,
        },
    )


def _resolve_sell_cost_basis(symbol: str, broker_avg_by_symbol: dict[str, float]) -> float:
    symbol_key = symbol.upper()
    broker_avg = broker_avg_by_symbol.get(symbol_key, 0.0)
    if broker_avg > 0:
        return broker_avg
    local_avg = get_position_avg_price(symbol_key)
    return local_avg or 0.0


def _held_symbols_for_decisions(symbols: list[str], broker: AlpacaBrokerClient | None = None) -> set[str]:
    """Use Alpaca as source of truth when available; local DB can be stale."""
    monitored = _monitored_symbol_set(symbols)
    if broker is not None:
        try:
            return _broker_long_symbols(broker, monitored)
        except BrokerAuthError as exc:
            logger.warning("broker.positions_unavailable reason=%s", exc)
    return _local_long_symbols(symbols)


def _combined_long_symbols(symbols: list[str], broker: AlpacaBrokerClient | None = None) -> set[str]:
    monitored = _monitored_symbol_set(symbols)
    held = _local_long_symbols(symbols)
    if broker is not None:
        try:
            held |= _broker_long_symbols(broker, monitored)
        except BrokerAuthError as exc:
            logger.warning("broker.positions_unavailable reason=%s", exc)
    return held


def _record_orphan_exit_proposals(symbols: list[str], orphan_symbols: list[str], source_job: str) -> None:
    for symbol in orphan_symbols:
        record_proposed_order(
            source_job,
            symbol,
            "EXIT",
            0.0,
            "orphan_broker_position_not_in_target_portfolio",
        )
        logger.info("decision.proposed symbol=%s action=EXIT reason=orphan_broker_position", symbol)


def run_once() -> None:
    started_at = datetime.now(timezone.utc)
    job_name = _job_name()
    if job_name in _SCHEDULED_TRADING_JOBS and not is_trading_weekday_utc(started_at):
        logger.info("job.skipped %s reason=non_trading_day utc_weekday=%s", job_name, started_at.weekday())
        return

    init_database()
    logger.info("job.start %s risk_appetite=%s", job_name, _risk_appetite())

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
        strategy = _portfolio_strategy()
        if strategy in {"momentum_rotation", "rotation", "momentum"}:
            summary = _run_momentum_rotation_decisioning(symbols, job_name)
            logger.info(
                "decision.rotation strategy=%s ranked=%s targets=%s",
                strategy,
                summary["ranked_count"],
                ",".join(summary["top_targets"]),  # type: ignore[arg-type]
            )
        else:
            summary = _run_trend_following_decisioning(symbols, job_name)
            logger.info("decision.trend_following strategy=%s", strategy)

        succeeded_count = len(summary["entered"]) + len(summary["held"]) + len(summary["exited"])  # type: ignore[arg-type]
        failed_count = 0
        status = "success"
        sendDailySummary(
            [
                f"job={job_name}",
                f"strategy={strategy}",
                f"symbols_with_bars={summary['considered_count']}",
                f"ranked={summary['ranked_count']}",
                f"top_targets={','.join(summary['top_targets'])}",  # type: ignore[arg-type]
                f"enters={','.join(summary['entered'])}",  # type: ignore[arg-type]
                f"holds={','.join(summary['held'])}",  # type: ignore[arg-type]
                f"exits={','.join(summary['exited'])}",  # type: ignore[arg-type]
                f"target_weight={summary['target_weight']}",
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
        broker_avg_by_symbol = {
            position.symbol: position.avg_entry_price
            for position in broker_positions
            if position.avg_entry_price > 0
        }
        broker_long_set = {symbol for symbol, qty in broker_qty_by_symbol.items() if qty > 0}
        monitored = _monitored_symbol_set(symbols)
        intended_long_set = set(enter_symbols + hold_symbols)

        if _auto_exit_orphan_positions():
            orphan_exits = sorted(
                symbol
                for symbol in broker_long_set
                if symbol.upper() in monitored and symbol not in intended_long_set and symbol not in exit_symbols
            )
            if orphan_exits:
                _record_orphan_exit_proposals(symbols, orphan_exits, job_name)
                exit_symbols = sorted(set(exit_symbols) | set(orphan_exits))
                logger.warning("order.orphan_exits symbols=%s", ",".join(orphan_exits))

        app_mode = _app_mode()
        trading_enabled = _trading_enabled()
        setting_enabled = _order_submission_enabled()
        submission_enabled = app_mode == "paper" and trading_enabled and setting_enabled
        max_open_positions = _max_open_positions()
        max_position_pct = _max_position_pct()
        submitted_count = 0
        rejected_count = 0
        buy_symbols = sorted(set(enter_symbols + hold_symbols))

        if submission_enabled:
            broker.ensure_paper_trading()
            account = broker.get_account_metrics()
            equity = float(account.get("equity", 0) or 0)
            cash = float(account.get("cash", 0) or 0)
            if equity <= 0:
                logger.warning("order.skipped reason=missing_account_equity")
            current_long_count = len([symbol for symbol, qty in broker_qty_by_symbol.items() if qty > 0])
            for symbol in buy_symbols:
                if equity <= 0:
                    break
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
                current_qty = float(broker_qty_by_symbol.get(symbol, 0) or 0)
                order_qty = _resolve_buy_qty(
                    broker=broker,
                    symbol=symbol,
                    proposal_weight=proposal_weight,
                    current_qty=current_qty,
                    equity=equity,
                    cash=cash,
                )
                if order_qty is None or order_qty < 1:
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
                        cash = max(0.0, cash - (filled_qty * filled_avg_price))
                    submitted_count += 1
                    current_long_count += 1
                    broker_qty_by_symbol[symbol] = current_qty + float(order.get("qty", order_qty))
                    sendTradeAlert(
                        symbol=symbol,
                        side="buy",
                        qty=request.qty,
                        broker_order_id=str(order.get("id", "")) or None,
                    )
                except OrderRejectedError as exc:
                    rejected_count += 1
                    logger.warning("order.rejected symbol=%s side=buy qty=%s reason=%s", symbol, request.qty, exc)
            for symbol in exit_symbols:
                qty = int(abs(broker_qty_by_symbol.get(symbol, 0)))
                if qty <= 0:
                    logger.info("order.skipped symbol=%s reason=no_broker_position_for_exit", symbol)
                    continue
                cost_basis = _resolve_sell_cost_basis(symbol, broker_avg_by_symbol)
                request = OrderRequest(symbol=symbol, qty=qty, side="sell")
                try:
                    order = broker.submit_paper_order(request)
                    filled_qty = float(order.get("filled_qty") or 0)
                    filled_avg_price = float(order.get("filled_avg_price") or 0)
                    trade_qty = filled_qty if filled_qty > 0 else float(qty)
                    pnl_result = None
                    if trade_qty > 0 and filled_avg_price > 0 and cost_basis > 0:
                        pnl_result = compute_realized_sell_pnl(
                            qty=trade_qty,
                            sell_price=filled_avg_price,
                            cost_basis=cost_basis,
                        )
                    realized_pnl_usd = pnl_result[0] if pnl_result else None
                    realized_pnl_pct = pnl_result[1] if pnl_result else None
                    local_order_id = record_broker_order(
                        broker_order_id=str(order.get("id", "")),
                        symbol=symbol,
                        qty=float(order.get("qty", qty)),
                        side=str(order.get("side", "sell")),
                        order_type=str(order.get("type", "market")),
                        status=str(order.get("status", "accepted")),
                        submitted_at=_parse_dt(order.get("submitted_at")),
                        filled_at=_parse_dt(order.get("filled_at")),
                        filled_avg_price=filled_avg_price if filled_avg_price > 0 else None,
                        cost_basis_avg=cost_basis if cost_basis > 0 else None,
                        realized_pnl_usd=realized_pnl_usd,
                        realized_pnl_pct=realized_pnl_pct,
                    )
                    if filled_qty > 0 and filled_avg_price > 0:
                        record_fill(
                            order_id=local_order_id,
                            symbol=symbol,
                            fill_qty=filled_qty,
                            fill_price=filled_avg_price,
                            fill_time=_parse_dt(order.get("filled_at")),
                        )
                    submitted_count += 1
                    sendTradeAlert(
                        symbol=symbol,
                        side="sell",
                        qty=request.qty,
                        broker_order_id=str(order.get("id", "")) or None,
                        fill_price=filled_avg_price if filled_avg_price > 0 else None,
                        cost_basis=cost_basis if cost_basis > 0 else None,
                        realized_pnl_usd=realized_pnl_usd,
                        realized_pnl_pct=realized_pnl_pct,
                    )
                except OrderRejectedError as exc:
                    rejected_count += 1
                    logger.warning("order.rejected symbol=%s side=sell qty=%s reason=%s", symbol, request.qty, exc)
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
            _record_reconcile_mismatch(
                job_name=job_name,
                missing_in_broker=missing_in_broker,
                unexpected_in_broker=unexpected_in_broker,
            )
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
            _record_reconcile_mismatch(
                job_name=job_name,
                missing_in_broker=[],
                unexpected_in_broker=[],
                missing_open_orders=missing_open_orders,
                unexpected_open_orders=unexpected_open_orders,
            )
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
                f"buy_candidates={','.join(buy_symbols)}",
                f"exits={','.join(exit_symbols)}",
                f"holds={','.join(hold_symbols)}",
                f"submitted={submitted_count}",
                f"rejected={rejected_count}",
                f"submission_enabled={submission_enabled}",
                f"order_sizing_mode={_order_sizing_mode()}",
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
        monitored = _monitored_symbol_set(symbols)
        orphan_exits = sorted(
            symbol for symbol in unexpected_in_broker if symbol.upper() in monitored
        )
        if orphan_exits and _auto_exit_orphan_positions():
            _record_orphan_exit_proposals(symbols, orphan_exits, job_name)
            unexpected_in_broker = sorted(set(unexpected_in_broker) - set(orphan_exits))
            logger.warning(
                "reconcile.orphan_exit_proposals recorded=%s",
                ",".join(orphan_exits),
            )
        if missing_in_broker or unexpected_in_broker:
            failed_count = 1
            status = "completed_with_errors"
            _record_reconcile_mismatch(
                job_name=job_name,
                missing_in_broker=missing_in_broker,
                unexpected_in_broker=unexpected_in_broker,
            )
            sendWarningAlert(
                "Reconcile mismatch",
                f"missing_in_broker={','.join(missing_in_broker) or 'none'} "
                f"unexpected_in_broker={','.join(unexpected_in_broker) or 'none'}",
            )
        else:
            status = "success"
            succeeded_count = len(intended_long_set)
            summary_lines = [
                f"job={job_name}",
                f"intended_positions={len(intended_long_set)}",
                f"broker_positions={len(broker_long_set)}",
                "status=success",
            ]
            if orphan_exits and _auto_exit_orphan_positions():
                summary_lines.append(f"orphan_exit_proposed={','.join(orphan_exits)}")
            sendDailySummary(summary_lines)
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
        try:
            status, succeeded_count, failed_count = _run_trading_pipeline_steps(include_order_execution=False)
        except Exception as exc:
            status = "failed"
            failed_count = 1
            sendCriticalAlert("Daily failure halt", f"postclose workflow halted: {exc}")
    elif job_name == "intraday_trading_workflow":
        try:
            status, succeeded_count, failed_count = _run_trading_pipeline_steps(include_order_execution=True)
        except Exception as exc:
            status = "failed"
            failed_count = 1
            sendCriticalAlert("Intraday workflow halt", f"intraday trading workflow halted: {exc}")
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
    job_name = _job_name()
    if job_name == "daily_summary":
        logger.error(
            "daily_summary is cron-only (Mon-Fri 21:15 UTC via knowetrade-daily-summary). "
            "Do not run it in the polling worker."
        )
        raise SystemExit(1)

    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    while True:
        if job_name in _SCHEDULED_TRADING_JOBS and not is_trading_weekday_utc():
            logger.info("worker.poll_skipped reason=non_trading_day job=%s", job_name)
            time.sleep(poll_seconds)
            continue
        try:
            run_once()
        except Exception as exc:  # pragma: no cover - scaffold error path
            logger.exception("job.failed %s", job_name)
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
