from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Signal:
    symbol: str
    action: str
    qty: int
    reference_price: float


def generate_signals(symbols: list[str]) -> list[Signal]:
    """Placeholder strategy: emit tiny BUY signals for monitored symbols."""
    signals: list[Signal] = []
    for symbol in symbols:
        signals.append(Signal(symbol=symbol.upper(), action="BUY", qty=1, reference_price=100.0))
    return signals
