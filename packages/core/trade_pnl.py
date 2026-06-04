from __future__ import annotations


def compute_realized_sell_pnl(*, qty: float, sell_price: float, cost_basis: float) -> tuple[float, float] | None:
    """Return (realized_pnl_usd, realized_pnl_pct) for a closed sell, or None if not computable."""
    if qty <= 0 or sell_price <= 0 or cost_basis <= 0:
        return None
    pnl_usd = (sell_price - cost_basis) * qty
    pnl_pct = (sell_price - cost_basis) / cost_basis
    return pnl_usd, pnl_pct


def format_realized_pnl_usd(pnl_usd: float) -> str:
    sign = "+" if pnl_usd >= 0 else "-"
    return f"{sign}${abs(pnl_usd):,.2f}"


def format_realized_pnl_pct(pnl_pct: float) -> str:
    sign = "+" if pnl_pct >= 0 else ""
    return f"{sign}{pnl_pct * 100:.2f}%"
