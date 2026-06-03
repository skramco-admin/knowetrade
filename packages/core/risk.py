from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    max_position_notional_usd: float


@dataclass(frozen=True)
class RiskAppetiteLimits:
    max_portfolio_positions: int
    max_open_positions: int
    max_position_pct: float
    paper_order_qty: int
    max_position_notional_usd: float


def normalize_risk_appetite(appetite: str | None = None) -> str:
    value = (appetite or os.getenv("RISK_APPETITE", "aggressive")).strip().lower().replace("-", "_")
    if value in {"conservative", "moderate", "aggressive", "ultra_aggressive"}:
        return value
    return "aggressive"


def limits_for_appetite(appetite: str) -> RiskAppetiteLimits:
    presets: dict[str, RiskAppetiteLimits] = {
        "conservative": RiskAppetiteLimits(5, 5, 0.20, 1, 10_000.0),
        "moderate": RiskAppetiteLimits(8, 8, 0.15, 2, 15_000.0),
        "aggressive": RiskAppetiteLimits(15, 15, 0.20, 3, 30_000.0),
        "ultra_aggressive": RiskAppetiteLimits(20, 20, 0.30, 5, 50_000.0),
    }
    return presets.get(normalize_risk_appetite(appetite), presets["aggressive"])


def resolve_risk_limits(appetite: str | None = None) -> RiskAppetiteLimits:
    preset = limits_for_appetite(normalize_risk_appetite(appetite))

    def _env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        return int(raw) if raw is not None and raw.strip() else default

    def _env_float(name: str, default: float) -> float:
        raw = os.getenv(name)
        return float(raw) if raw is not None and raw.strip() else default

    max_portfolio = _env_int("MAX_PORTFOLIO_POSITIONS", preset.max_portfolio_positions)
    max_open = _env_int("MAX_OPEN_POSITIONS", preset.max_open_positions)
    return RiskAppetiteLimits(
        max_portfolio_positions=max_portfolio,
        max_open_positions=max_open,
        max_position_pct=_env_float("MAX_POSITION_PCT", preset.max_position_pct),
        paper_order_qty=_env_int("PAPER_ORDER_QTY", preset.paper_order_qty),
        max_position_notional_usd=_env_float("MAX_POSITION_NOTIONAL_USD", preset.max_position_notional_usd),
    )


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
