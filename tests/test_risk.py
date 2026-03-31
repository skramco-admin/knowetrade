from packages.core.risk import RiskConfig, can_place_order


def test_v1_is_long_only() -> None:
    allowed, reason = can_place_order(
        symbol="SPY",
        side="SELL",
        qty=1,
        price=100.0,
        risk_config=RiskConfig(max_position_notional_usd=1000.0),
    )
    assert allowed is False
    assert "long-only" in reason
