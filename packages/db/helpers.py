from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import Base, JobRun, Order, Position, RiskEvent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./knowetrade.db")
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


def init_database() -> None:
    Base.metadata.create_all(bind=ENGINE)


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
        session.add(
            Position(
                symbol=symbol,
                qty=float(qty),
                avg_price=100.0,
            )
        )
