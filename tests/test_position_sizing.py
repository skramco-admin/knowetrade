from packages.core.position_sizing import compute_target_buy_qty, normalize_order_sizing_mode


def test_compute_target_buy_qty_full_enter() -> None:
    # $100k equity, 5% target, $500 ETF -> $5k / $500 = 10 shares
    qty = compute_target_buy_qty(
        equity=100_000.0,
        cash=50_000.0,
        target_weight=0.05,
        price=500.0,
        current_qty=0.0,
        max_position_pct=0.30,
        max_position_notional_usd=50_000.0,
    )
    assert qty == 10


def test_compute_target_buy_qty_capped_by_cash() -> None:
    qty = compute_target_buy_qty(
        equity=100_000.0,
        cash=1_000.0,
        target_weight=0.05,
        price=500.0,
        current_qty=0.0,
        max_position_pct=0.30,
        max_position_notional_usd=50_000.0,
    )
    assert qty == 2


def test_compute_target_buy_qty_already_at_target() -> None:
    qty = compute_target_buy_qty(
        equity=100_000.0,
        cash=50_000.0,
        target_weight=0.05,
        price=500.0,
        current_qty=10.0,
        max_position_pct=0.30,
        max_position_notional_usd=50_000.0,
    )
    assert qty == 0


def test_compute_target_buy_qty_top_up() -> None:
    qty = compute_target_buy_qty(
        equity=100_000.0,
        cash=50_000.0,
        target_weight=0.05,
        price=500.0,
        current_qty=5.0,
        max_position_pct=0.30,
        max_position_notional_usd=50_000.0,
    )
    assert qty == 5


def test_normalize_order_sizing_mode() -> None:
    assert normalize_order_sizing_mode("equity-weighted") == "equity_weighted"
    assert normalize_order_sizing_mode("fixed_qty") == "fixed_qty"
    assert normalize_order_sizing_mode(None) == "equity_weighted"
