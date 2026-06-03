from packages.core.rotation import RankedSymbol, build_rotation_decision, rank_symbols_by_momentum


def test_rank_symbols_by_momentum_orders_highest_first() -> None:
    closes = {symbol: [100.0 + index for index in range(30)] for symbol in ("AAA", "BBB", "CCC")}
    closes["AAA"] = [100.0] * 29 + [110.0]
    closes["BBB"] = [100.0] * 29 + [105.0]
    closes["CCC"] = [100.0] * 29 + [102.0]
    ranked = rank_symbols_by_momentum(closes)
    assert [row.symbol for row in ranked] == ["AAA", "BBB", "CCC"]


def test_build_rotation_decision_enters_exits_and_holds() -> None:
    ranked = [
        RankedSymbol("AAA", 0.10),
        RankedSymbol("BBB", 0.08),
        RankedSymbol("CCC", 0.05),
    ]
    decision = build_rotation_decision(
        ranked=ranked,
        currently_held={"OLD", "BBB"},
        max_positions=2,
        max_position_pct=0.30,
    )
    assert decision.target_set == frozenset({"AAA", "BBB"})
    assert decision.entered == ("AAA",)
    assert decision.held == ("BBB",)
    assert decision.exited == ("OLD",)
    assert decision.target_weight == 0.30


def test_symbols_without_enough_bars_are_excluded_from_ranking() -> None:
    ranked = rank_symbols_by_momentum({"SHORT": [1.0, 2.0, 3.0]})
    assert ranked == []
