from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from packages.db.helpers import init_database, list_job_runs, list_positions

app = FastAPI(title="KnoweTrade API", version="0.1.0")


def _require_admin_key(x_admin_key: str | None) -> None:
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "knowetrade-api", "message": "API running"}


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/admin/positions")
def admin_positions(x_admin_key: str | None = Header(default=None)) -> list[dict[str, Any]]:
    _require_admin_key(x_admin_key)
    return list_positions(limit=100)


@app.get("/admin/job-runs")
def admin_job_runs(x_admin_key: str | None = Header(default=None)) -> list[dict[str, Any]]:
    _require_admin_key(x_admin_key)
    return list_job_runs(limit=100)
