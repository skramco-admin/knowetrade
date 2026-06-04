from __future__ import annotations

import math


def compute_target_buy_qty(
    *,
    equity: float,
    cash: float,
    target_weight: float,
    price: float,
    current_qty: float = 0.0,
    max_position_pct: float,
    max_position_notional_usd: float,
) -> int:
    """
    Shares to buy so the position moves toward target_weight of account equity.

    Returns 0 when no buy is warranted (already at/above target, bad inputs, or insufficient cash).
    """
    if equity <= 0 or price <= 0 or target_weight <= 0:
        return 0

    weight_cap = min(target_weight, max_position_pct)
    target_notional = min(equity * weight_cap, max_position_notional_usd)
    current_notional = max(current_qty, 0.0) * price
    needed_notional = target_notional - current_notional
    if needed_notional <= 0:
        return 0

    raw_qty = math.floor(needed_notional / price)
    if raw_qty < 1:
        return 0

    affordable_qty = math.floor(max(cash, 0.0) / price)
    if affordable_qty < 1:
        return 0

    return int(min(raw_qty, affordable_qty))


def normalize_order_sizing_mode(mode: str | None = None) -> str:
    value = (mode or "equity_weighted").strip().lower().replace("-", "_")
    if value in {"equity_weighted", "equity", "target_weight", "weighted"}:
        return "equity_weighted"
    if value in {"fixed_qty", "fixed", "legacy"}:
        return "fixed_qty"
    return "equity_weighted"
