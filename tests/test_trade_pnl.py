from packages.core.trade_pnl import compute_realized_sell_pnl, format_realized_pnl_pct, format_realized_pnl_usd


def test_compute_realized_sell_pnl_profit() -> None:
    result = compute_realized_sell_pnl(qty=5, sell_price=110.0, cost_basis=100.0)
    assert result is not None
    pnl_usd, pnl_pct = result
    assert pnl_usd == 50.0
    assert abs(pnl_pct - 0.10) < 1e-9


def test_compute_realized_sell_pnl_loss() -> None:
    result = compute_realized_sell_pnl(qty=2, sell_price=90.0, cost_basis=100.0)
    assert result is not None
    pnl_usd, pnl_pct = result
    assert pnl_usd == -20.0
    assert abs(pnl_pct + 0.10) < 1e-9


def test_compute_realized_sell_pnl_missing_inputs() -> None:
    assert compute_realized_sell_pnl(qty=0, sell_price=10.0, cost_basis=10.0) is None
    assert compute_realized_sell_pnl(qty=1, sell_price=0, cost_basis=10.0) is None


def test_format_realized_pnl() -> None:
    assert format_realized_pnl_usd(12.5) == "+$12.50"
    assert format_realized_pnl_usd(-3.2) == "-$3.20"
    assert format_realized_pnl_pct(0.0525) == "+5.25%"
