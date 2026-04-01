from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import (
    AuditLog,
    Base,
    Fill,
    JobRun,
    Order,
    Position,
    PriceBar,
    ProposedOrder,
    RiskEvent,
    Setting,
    Signal,
    Symbol,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./knowetrade.db")
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


def init_database() -> None:
    Base.metadata.create_all(bind=ENGINE)
    _ensure_symbols_schema_compat()
    _ensure_signals_schema_compat()
    _ensure_proposed_orders_schema_compat()
    _ensure_orders_schema_compat()
    _ensure_settings_audit_schema_compat()


def _ensure_symbols_schema_compat() -> None:
    inspector = inspect(ENGINE)
    tables = inspector.get_table_names()
    if "symbols" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("symbols")}
    dialect = ENGINE.dialect.name

    statements: list[str] = []
    if "asset_class" not in columns:
        statements.append("alter table symbols add column asset_class text")
    if "strategy_bucket" not in columns:
        statements.append("alter table symbols add column strategy_bucket text")
    if "created_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table symbols add column created_at datetime")
        else:
            statements.append("alter table symbols add column created_at timestamptz")
    if "updated_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table symbols add column updated_at datetime")
        else:
            statements.append("alter table symbols add column updated_at timestamptz")

    if not statements:
        return

    with ENGINE.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        if dialect == "sqlite":
            connection.execute(
                text(
                    """
                    update symbols
                    set
                      asset_class = coalesce(asset_class, 'ETF'),
                      strategy_bucket = coalesce(strategy_bucket, 'etf_trend'),
                      created_at = coalesce(created_at, datetime('now')),
                      updated_at = coalesce(updated_at, datetime('now'))
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    update symbols
                    set
                      asset_class = coalesce(asset_class, 'ETF'),
                      strategy_bucket = coalesce(strategy_bucket, 'etf_trend'),
                      created_at = coalesce(created_at, now()),
                      updated_at = coalesce(updated_at, now())
                    """
                )
            )


def _ensure_signals_schema_compat() -> None:
    inspector = inspect(ENGINE)
    tables = inspector.get_table_names()
    if "signals" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("signals")}
    dialect = ENGINE.dialect.name
    statements: list[str] = []
    if "reason" not in columns:
        statements.append("alter table signals add column reason text")
    if "signal_time" not in columns:
        if dialect == "sqlite":
            statements.append("alter table signals add column signal_time datetime")
        else:
            statements.append("alter table signals add column signal_time timestamptz")

    if not statements:
        return

    with ENGINE.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        if dialect == "sqlite":
            connection.execute(
                text(
                    """
                    update signals
                    set signal_time = coalesce(signal_time, created_at, datetime('now'))
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    update signals
                    set signal_time = coalesce(signal_time, created_at, now())
                    """
                )
            )


def _ensure_proposed_orders_schema_compat() -> None:
    inspector = inspect(ENGINE)
    tables = inspector.get_table_names()
    if "proposed_orders" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("proposed_orders")}
    dialect = ENGINE.dialect.name
    statements: list[str] = []
    if "job_name" not in columns:
        statements.append("alter table proposed_orders add column job_name text")
    if "target_weight" not in columns:
        statements.append("alter table proposed_orders add column target_weight double precision")
    if "reason" not in columns:
        statements.append("alter table proposed_orders add column reason text")
    if "created_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table proposed_orders add column created_at datetime")
        else:
            statements.append("alter table proposed_orders add column created_at timestamptz")

    if not statements:
        return

    with ENGINE.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        if dialect == "sqlite":
            connection.execute(
                text(
                    """
                    update proposed_orders
                    set
                      job_name = coalesce(job_name, 'dry_run_portfolio_decisioning'),
                      target_weight = coalesce(target_weight, 0),
                      reason = coalesce(reason, ''),
                      created_at = coalesce(created_at, datetime('now'))
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    update proposed_orders
                    set
                      job_name = coalesce(job_name, 'dry_run_portfolio_decisioning'),
                      target_weight = coalesce(target_weight, 0),
                      reason = coalesce(reason, ''),
                      created_at = coalesce(created_at, now())
                    """
                )
            )


def _ensure_orders_schema_compat() -> None:
    inspector = inspect(ENGINE)
    tables = inspector.get_table_names()
    if "orders" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    dialect = ENGINE.dialect.name
    statements: list[str] = []
    if "order_type" not in columns:
        statements.append("alter table orders add column order_type text")
    if "submitted_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table orders add column submitted_at datetime")
        else:
            statements.append("alter table orders add column submitted_at timestamptz")
    if "filled_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table orders add column filled_at datetime")
        else:
            statements.append("alter table orders add column filled_at timestamptz")
    if "updated_at" not in columns:
        if dialect == "sqlite":
            statements.append("alter table orders add column updated_at datetime")
        else:
            statements.append("alter table orders add column updated_at timestamptz")

    if statements:
        with ENGINE.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            if dialect == "sqlite":
                connection.execute(
                    text(
                        """
                        update orders
                        set
                          order_type = coalesce(order_type, 'market'),
                          submitted_at = coalesce(submitted_at, created_at, datetime('now')),
                          updated_at = coalesce(updated_at, created_at, datetime('now'))
                        """
                    )
                )
            else:
                connection.execute(
                    text(
                        """
                        update orders
                        set
                          order_type = coalesce(order_type, 'market'),
                          submitted_at = coalesce(submitted_at, created_at, now()),
                          updated_at = coalesce(updated_at, created_at, now())
                        """
                    )
                )

    if "fills" not in tables:
        return

    fill_columns = {column["name"] for column in inspector.get_columns("fills")}
    fill_statements: list[str] = []
    if "symbol" not in fill_columns:
        fill_statements.append("alter table fills add column symbol text")
    if "fill_time" not in fill_columns:
        if dialect == "sqlite":
            fill_statements.append("alter table fills add column fill_time datetime")
        else:
            fill_statements.append("alter table fills add column fill_time timestamptz")

    if not fill_statements:
        return

    with ENGINE.begin() as connection:
        for statement in fill_statements:
            connection.execute(text(statement))
        if dialect == "sqlite":
            connection.execute(
                text(
                    """
                    update fills
                    set
                      symbol = coalesce(symbol, ''),
                      fill_time = coalesce(fill_time, created_at, datetime('now'))
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    update fills
                    set
                      symbol = coalesce(symbol, ''),
                      fill_time = coalesce(fill_time, created_at, now())
                    """
                )
            )


def _ensure_settings_audit_schema_compat() -> None:
    inspector = inspect(ENGINE)
    tables = inspector.get_table_names()
    if "audit_logs" not in tables:
        dialect = ENGINE.dialect.name
        with ENGINE.begin() as connection:
            if dialect == "sqlite":
                connection.execute(
                    text(
                        """
                        create table if not exists audit_logs (
                          id integer primary key autoincrement,
                          event_type text not null,
                          actor text not null default 'system',
                          details text not null default '',
                          created_at datetime not null default (datetime('now'))
                        )
                        """
                    )
                )
            else:
                connection.execute(
                    text(
                        """
                        create table if not exists audit_logs (
                          id bigserial primary key,
                          event_type text not null,
                          actor text not null default 'system',
                          details text not null default '',
                          created_at timestamptz not null default now()
                        )
                        """
                    )
                )


@contextmanager
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_positions(limit: int = 100) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = session.execute(select(Position).order_by(Position.id.desc()).limit(limit)).scalars().all()
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "qty": row.qty,
                "avg_price": row.avg_price,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]


def list_symbols(limit: int = 1000) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(select(Symbol).order_by(Symbol.is_active.desc(), Symbol.ticker.asc()).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "ticker": row.ticker,
                "asset_class": row.asset_class,
                "strategy_bucket": row.strategy_bucket,
                "is_active": bool(row.is_active),
            }
            for row in rows
        ]


def list_active_etf_symbols(strategy_bucket: str = "etf_trend") -> list[str]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(
                select(Symbol.ticker)
                .where(Symbol.is_active.is_(True))
                .where(Symbol.asset_class == "ETF")
                .where(Symbol.strategy_bucket == strategy_bucket)
                .order_by(Symbol.ticker.asc())
            )
            .scalars()
            .all()
        )
        return [str(ticker).upper() for ticker in rows]


def upsert_price_bar(
    *,
    symbol: str,
    bar_time: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
    timeframe: str = "1d",
) -> None:
    init_database()
    with db_session() as session:
        existing = (
            session.execute(
                select(PriceBar).where(
                    PriceBar.symbol == symbol.upper(),
                    PriceBar.timeframe == timeframe,
                    PriceBar.bar_time == bar_time,
                )
            )
            .scalars()
            .first()
        )
        if existing is None:
            session.add(
                PriceBar(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    bar_time=bar_time,
                    open=float(open_price),
                    high=float(high_price),
                    low=float(low_price),
                    close=float(close_price),
                    volume=int(volume),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            return

        existing.open = float(open_price)
        existing.high = float(high_price)
        existing.low = float(low_price)
        existing.close = float(close_price)
        existing.volume = int(volume)
        existing.updated_at = datetime.now(timezone.utc)


def list_recent_price_bars(symbol: str, limit: int = 120) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(
                select(PriceBar)
                .where(PriceBar.symbol == symbol.upper())
                .where(PriceBar.timeframe == "1d")
                .order_by(PriceBar.bar_time.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [
            {
                "symbol": row.symbol,
                "bar_time": row.bar_time,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": int(row.volume),
            }
            for row in rows
        ]


def record_signal(symbol: str, signal_type: str, strength: float, reason: str) -> None:
    init_database()
    with db_session() as session:
        session.add(
            Signal(
                symbol=symbol.upper(),
                signal_type=signal_type,
                strength=float(strength),
                reason=reason,
                signal_time=datetime.now(timezone.utc),
            )
        )


def list_signals(limit: int = 200) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(select(Signal).order_by(Signal.id.desc()).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "signal": row.signal_type,
                "strength": float(row.strength),
                "reason": row.reason or "",
                "signal_time": row.signal_time.isoformat() if row.signal_time else None,
            }
            for row in rows
        ]


def list_latest_signals_for_symbols(symbols: list[str]) -> list[dict[str, Any]]:
    init_database()
    if not symbols:
        return []
    wanted = {symbol.upper() for symbol in symbols}
    with db_session() as session:
        rows = (
            session.execute(
                select(Signal)
                .where(Signal.symbol.in_(wanted))
                .order_by(Signal.symbol.asc(), Signal.signal_time.desc(), Signal.id.desc())
            )
            .scalars()
            .all()
        )
        latest_by_symbol: dict[str, Signal] = {}
        for row in rows:
            symbol = row.symbol.upper()
            if symbol in latest_by_symbol:
                continue
            latest_by_symbol[symbol] = row
        return [
            {
                "symbol": symbol,
                "signal": row.signal_type,
                "strength": float(row.strength),
                "reason": row.reason or "",
                "signal_time": row.signal_time.isoformat() if row.signal_time else None,
            }
            for symbol, row in sorted(latest_by_symbol.items(), key=lambda item: item[0])
        ]


def list_position_qty_by_symbols(symbols: list[str]) -> dict[str, float]:
    init_database()
    if not symbols:
        return {}
    wanted = [symbol.upper() for symbol in symbols]
    with db_session() as session:
        rows = (
            session.execute(
                select(Position.symbol, func.coalesce(func.sum(Position.qty), 0.0))
                .where(Position.symbol.in_(wanted))
                .group_by(Position.symbol)
            )
            .all()
        )
        return {str(symbol).upper(): float(qty) for symbol, qty in rows}


def record_proposed_order(job_name: str, symbol: str, action: str, target_weight: float, reason: str) -> None:
    init_database()
    with db_session() as session:
        session.add(
            ProposedOrder(
                job_name=job_name,
                symbol=symbol.upper(),
                action=action,
                target_weight=float(target_weight),
                reason=reason,
                created_at=datetime.now(timezone.utc),
            )
        )


def list_proposed_orders(limit: int = 500) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(select(ProposedOrder).order_by(ProposedOrder.id.desc()).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "job_name": row.job_name,
                "symbol": row.symbol,
                "action": row.action,
                "target_weight": float(row.target_weight),
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]


def get_setting_bool(key: str, default: bool = False) -> bool:
    init_database()
    with db_session() as session:
        row = session.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
        if row is None:
            return default
        value = row.value
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return bool(value)


def set_setting_bool(key: str, value: bool, description: str | None = None) -> None:
    init_database()
    with db_session() as session:
        existing = session.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
        if existing is None:
            session.add(
                Setting(
                    key=key,
                    value=bool(value),
                    description=description,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            return
        existing.value = bool(value)
        if description:
            existing.description = description
        existing.updated_at = datetime.now(timezone.utc)


def append_audit_log(event_type: str, details: str, actor: str = "system") -> None:
    init_database()
    with db_session() as session:
        session.add(
            AuditLog(
                event_type=event_type,
                actor=actor,
                details=details,
                created_at=datetime.now(timezone.utc),
            )
        )


def list_risk_events(limit: int = 200) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(select(RiskEvent).order_by(RiskEvent.id.desc()).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "symbol": row.symbol,
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]


def list_latest_proposed_orders_for_symbols(symbols: list[str]) -> list[dict[str, Any]]:
    init_database()
    if not symbols:
        return []
    wanted = {symbol.upper() for symbol in symbols}
    with db_session() as session:
        rows = (
            session.execute(
                select(ProposedOrder)
                .where(ProposedOrder.symbol.in_(wanted))
                .order_by(ProposedOrder.symbol.asc(), ProposedOrder.created_at.desc(), ProposedOrder.id.desc())
            )
            .scalars()
            .all()
        )
        latest_by_symbol: dict[str, ProposedOrder] = {}
        for row in rows:
            symbol = row.symbol.upper()
            if symbol in latest_by_symbol:
                continue
            latest_by_symbol[symbol] = row
        return [
            {
                "symbol": symbol,
                "action": row.action,
                "target_weight": float(row.target_weight),
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for symbol, row in sorted(latest_by_symbol.items(), key=lambda item: item[0])
        ]


def list_orders(limit: int = 500) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = (
            session.execute(select(Order).order_by(Order.id.desc()).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "broker_order_id": row.broker_order_id,
                "symbol": row.symbol,
                "qty": float(row.qty),
                "side": row.side,
                "order_type": row.order_type,
                "status": row.status,
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                "filled_at": row.filled_at.isoformat() if row.filled_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]


def record_broker_order(
    *,
    broker_order_id: str,
    symbol: str,
    qty: float,
    side: str,
    order_type: str,
    status: str,
    submitted_at: datetime | None,
    filled_at: datetime | None,
) -> int:
    init_database()
    with db_session() as session:
        existing = session.execute(select(Order).where(Order.broker_order_id == broker_order_id)).scalar_one_or_none()
        if existing is None:
            order = Order(
                broker_order_id=broker_order_id,
                symbol=symbol.upper(),
                qty=float(qty),
                side=side.lower(),
                order_type=order_type.lower() if order_type else "market",
                status=status.lower(),
                submitted_at=submitted_at or datetime.now(timezone.utc),
                filled_at=filled_at,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(order)
            session.flush()
            return int(order.id)

        existing.symbol = symbol.upper()
        existing.qty = float(qty)
        existing.side = side.lower()
        existing.order_type = order_type.lower() if order_type else "market"
        existing.status = status.lower()
        existing.submitted_at = submitted_at or existing.submitted_at
        existing.filled_at = filled_at
        existing.updated_at = datetime.now(timezone.utc)
        session.flush()
        return int(existing.id)


def record_fill(order_id: int, symbol: str, fill_qty: float, fill_price: float, fill_time: datetime | None) -> None:
    init_database()
    with db_session() as session:
        session.add(
            Fill(
                order_id=order_id,
                symbol=symbol.upper(),
                fill_qty=float(fill_qty),
                fill_price=float(fill_price),
                fill_time=fill_time or datetime.now(timezone.utc),
            )
        )


def get_position_qty(symbol: str) -> float:
    init_database()
    with db_session() as session:
        qty = session.execute(
            select(func.coalesce(func.sum(Position.qty), 0.0)).where(Position.symbol == symbol.upper())
        ).scalar_one()
        return float(qty)


def list_job_runs(limit: int = 100) -> list[dict[str, Any]]:
    init_database()
    with db_session() as session:
        rows = session.execute(select(JobRun).order_by(JobRun.id.desc()).limit(limit)).scalars().all()
        return [
            {
                "id": row.id,
                "job_name": row.job_name,
                "status": row.status,
                "started_at": row.started_at.isoformat(),
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in rows
        ]


def log_job_run(job_name: str, status: str, started_at: datetime) -> None:
    init_database()
    with db_session() as session:
        session.add(
            JobRun(
                job_name=job_name,
                status=status,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        )


def record_risk_event(symbol: str, reason: str) -> None:
    init_database()
    with db_session() as session:
        session.add(RiskEvent(symbol=symbol, reason=reason))


def record_order_and_position(order_id: str, symbol: str, qty: int) -> None:
    init_database()
    with db_session() as session:
        session.add(
            Order(
                broker_order_id=order_id,
                symbol=symbol,
                qty=float(qty),
                side="buy",
                status="accepted",
            )
        )
        existing = session.execute(select(Position).where(Position.symbol == symbol)).scalar_one_or_none()
        if existing is None:
            session.add(
                Position(
                    symbol=symbol,
                    qty=float(qty),
                    avg_price=100.0,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            return

        # Basic long-only weighted-average position update for scaffold behavior.
        fill_qty = float(qty)
        fill_price = 100.0
        total_qty = float(existing.qty) + fill_qty
        if total_qty <= 0:
            existing.qty = 0.0
            existing.avg_price = 0.0
        else:
            existing.avg_price = ((float(existing.qty) * float(existing.avg_price)) + (fill_qty * fill_price)) / total_qty
            existing.qty = total_qty
        existing.updated_at = datetime.now(timezone.utc)
