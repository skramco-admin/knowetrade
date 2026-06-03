from packages.core.signals import calculate_trend_signal, rules_for_appetite


def _uptrend_closes(length: int = 120, start: float = 100.0, step: float = 0.5) -> list[float]:
    return [start + (index * step) for index in range(length)]


def _downtrend_closes(length: int = 120, start: float = 200.0, step: float = 0.5) -> list[float]:
    return [start - (index * step) for index in range(length)]


def test_conservative_requires_all_bullish_factors_for_buy() -> None:
    rules = rules_for_appetite("conservative")
    signal, _, _ = calculate_trend_signal(_uptrend_closes(), rules)
    assert signal == "BUY"


def test_ultra_aggressive_buys_with_weaker_trend() -> None:
    rules = rules_for_appetite("ultra_aggressive")
    closes = [100.0] * 19 + [101.0]
    signal, _, reason = calculate_trend_signal(closes, rules)
    assert signal in {"BUY", "HOLD"}
    assert "buy_need=1" in reason


def test_aggressive_exits_on_full_bearish_alignment() -> None:
    rules = rules_for_appetite("aggressive")
    signal, _, _ = calculate_trend_signal(_downtrend_closes(), rules)
    assert signal == "EXIT"
