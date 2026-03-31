from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    max_position_notional_usd: float


def can_place_order(
    symbol: str,
    side: str,
    qty: int,
    price: float,
    risk_config: RiskConfig,
) -> tuple[bool, str]:
    """Long-only v1 risk gate with simple notional guard."""
    _ = symbol
    if side.upper() != "BUY":
        return False, "v1 is long-only; non-BUY orders are blocked"

    if qty <= 0:
        return False, "qty must be positive"

    notional = qty * price
    if notional > risk_config.max_position_notional_usd:
        return False, "order notional exceeds MAX_POSITION_NOTIONAL_USD"

    return True, "ok"
