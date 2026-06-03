from __future__ import annotations

from dataclasses import dataclass


def momentum_return(closes: list[float], lookback: int = 20) -> float | None:
    """Trailing momentum: (latest / lookback-ago) - 1."""
    if len(closes) < lookback + 1:
        return None
    base = closes[-(lookback + 1)]
    if base == 0:
        return None
    return (closes[-1] / base) - 1.0


@dataclass(frozen=True)
class RankedSymbol:
    symbol: str
    momentum: float


@dataclass(frozen=True)
class RotationDecision:
    target_set: frozenset[str]
    entered: tuple[str, ...]
    held: tuple[str, ...]
    exited: tuple[str, ...]
    target_weight: float
    ranked: tuple[RankedSymbol, ...]


def rank_symbols_by_momentum(
    symbol_closes: dict[str, list[float]],
    *,
    lookback: int = 20,
) -> list[RankedSymbol]:
    ranked: list[RankedSymbol] = []
    for symbol in sorted(symbol_closes):
        momentum = momentum_return(symbol_closes[symbol], lookback=lookback)
        if momentum is None:
            continue
        ranked.append(RankedSymbol(symbol=symbol.upper(), momentum=momentum))
    ranked.sort(key=lambda row: (-row.momentum, row.symbol))
    return ranked


def build_rotation_decision(
    *,
    ranked: list[RankedSymbol],
    currently_held: set[str],
    max_positions: int,
    max_position_pct: float,
) -> RotationDecision:
    top = ranked[: max(0, max_positions)]
    target_set = {row.symbol for row in top}
    held_set = {symbol.upper() for symbol in currently_held}
    entered = sorted(target_set - held_set)
    held = sorted(target_set & held_set)
    exited = sorted(held_set - target_set)
    equal_weight = (1.0 / len(target_set)) if target_set else 0.0
    target_weight = min(equal_weight, max_position_pct)
    return RotationDecision(
        target_set=frozenset(target_set),
        entered=tuple(entered),
        held=tuple(held),
        exited=tuple(exited),
        target_weight=target_weight,
        ranked=tuple(top),
    )


def rotation_reason(*, action: str, symbol: str, rank: int | None, momentum: float | None, target_weight: float) -> str:
    rank_text = f"rank={rank}" if rank is not None else "rank=n/a"
    momentum_text = f"momentum20={momentum:.6f}" if momentum is not None else "momentum20=n/a"
    if action == "EXIT":
        return f"rotation_{action.lower()} {rank_text} {momentum_text} target_weight=0.0000"
    return f"rotation_{action.lower()} {rank_text} {momentum_text} equal_weight={target_weight:.4f}"
