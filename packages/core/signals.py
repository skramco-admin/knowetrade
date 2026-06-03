from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from packages.core.rotation import momentum_return

@dataclass(frozen=True)
class TrendSignalRules:
    min_bars: int
    buy_score_required: int
    exit_score_required: int


def rules_for_appetite(appetite: str) -> TrendSignalRules:
    normalized = appetite.strip().lower().replace("-", "_")
    presets: dict[str, TrendSignalRules] = {
        "conservative": TrendSignalRules(min_bars=100, buy_score_required=3, exit_score_required=3),
        "moderate": TrendSignalRules(min_bars=50, buy_score_required=2, exit_score_required=3),
        "aggressive": TrendSignalRules(min_bars=50, buy_score_required=2, exit_score_required=3),
        "ultra_aggressive": TrendSignalRules(min_bars=20, buy_score_required=1, exit_score_required=3),
    }
    return presets.get(normalized, presets["aggressive"])


def calculate_trend_signal(
    closes: list[float],
    rules: TrendSignalRules,
) -> tuple[str, float, str]:
    if len(closes) < rules.min_bars:
        return "HOLD", 0.0, f"insufficient_data_need_{rules.min_bars}d"

    latest_close = closes[-1]
    sma20 = mean(closes[-20:])
    sma50 = mean(closes[-50:]) if len(closes) >= 50 else sma20
    sma100 = mean(closes[-100:]) if len(closes) >= 100 else sma50
    momentum20 = 0.0
    computed = momentum_return(closes, lookback=20)
    if computed is not None:
        momentum20 = computed

    bullish_factors = [
        latest_close > sma50,
        sma20 > sma50,
        momentum20 > 0,
    ]
    bearish_factors = [
        latest_close < sma50,
        sma20 < sma50,
        momentum20 < 0,
    ]
    bullish_score = sum(bullish_factors)
    bearish_score = sum(bearish_factors)

    if bullish_score >= rules.buy_score_required:
        signal = "BUY"
    elif bearish_score >= rules.exit_score_required:
        signal = "EXIT"
    else:
        signal = "HOLD"

    reason = (
        f"close={latest_close:.4f} sma20={sma20:.4f} sma50={sma50:.4f} "
        f"sma100={sma100:.4f} momentum20={momentum20:.6f} "
        f"bullish_score={bullish_score} bearish_score={bearish_score} "
        f"buy_need={rules.buy_score_required} exit_need={rules.exit_score_required}"
    )
    return signal, momentum20, reason
