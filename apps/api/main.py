from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from packages.broker_alpaca.client import AlpacaBrokerClient
from packages.db.helpers import (
    append_audit_log,
    get_setting_bool,
    init_database,
    list_job_runs,
    list_orders,
    list_positions,
    list_proposed_orders,
    list_risk_events,
    list_signals,
    list_symbols,
    set_setting_bool,
)

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


@app.get("/health/deps")
def health_deps() -> dict[str, Any]:
    app_mode = os.getenv("APP_MODE", "paper").strip().lower()
    env_enable = os.getenv("ENABLE_ORDER_SUBMISSION")
    if env_enable is None:
        enable_order_submission = get_setting_bool("paper_order_submission_enabled", default=False)
    else:
        enable_order_submission = env_enable.strip().lower() == "true"
    trading_enabled = os.getenv("TRADING_ENABLED", "false").strip().lower() == "true"
    database_configured = bool(os.getenv("DATABASE_URL"))
    database_ok = False
    try:
        init_database()
        database_ok = True
    except Exception:
        database_ok = False
    alpaca_paper = "paper-api.alpaca.markets" in os.getenv("ALPACA_BASE_URL", "")
    alpaca_auth_ok = False
    try:
        client = AlpacaBrokerClient()
        client.validate_auth_strict()
        alpaca_auth_ok = True
    except Exception:
        alpaca_auth_ok = False
    return {
        "status": "ok",
        "app_mode": app_mode,
        "database_configured": database_configured,
        "database_ok": database_ok,
        "alpaca_paper_endpoint": alpaca_paper,
        "alpaca_auth_ok": alpaca_auth_ok,
        "trading_enabled": trading_enabled,
        "enable_order_submission": enable_order_submission,
    }


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


@app.get("/symbols")
def symbols() -> list[dict[str, Any]]:
    return list_symbols(limit=2000)


@app.get("/positions")
def positions() -> list[dict[str, Any]]:
    return list_positions(limit=500)


@app.get("/orders")
def orders() -> list[dict[str, Any]]:
    return list_orders(limit=500)


@app.get("/job-runs")
def job_runs() -> list[dict[str, Any]]:
    return list_job_runs(limit=500)


@app.get("/risk-events")
def risk_events() -> list[dict[str, Any]]:
    return list_risk_events(limit=500)


@app.get("/signals")
def signals() -> list[dict[str, Any]]:
    return list_signals(limit=500)


@app.get("/proposed-orders")
def proposed_orders() -> list[dict[str, Any]]:
    return list_proposed_orders(limit=500)


@app.get("/account-metrics")
def account_metrics() -> dict[str, Any]:
    client = AlpacaBrokerClient()
    return client.get_account_metrics()


@app.post("/admin/paper-trading/enable")
def enable_paper_trading(x_admin_key: str | None = Header(default=None)) -> dict[str, Any]:
    _require_admin_key(x_admin_key)
    set_setting_bool("paper_order_submission_enabled", True, "paper trading order submission toggle")
    append_audit_log("paper_trading_toggle", "enabled via admin API", actor="admin")
    return {"status": "ok", "paper_order_submission_enabled": True}


@app.post("/admin/paper-trading/disable")
def disable_paper_trading(x_admin_key: str | None = Header(default=None)) -> dict[str, Any]:
    _require_admin_key(x_admin_key)
    set_setting_bool("paper_order_submission_enabled", False, "paper trading order submission toggle")
    append_audit_log("paper_trading_toggle", "disabled via admin API", actor="admin")
    return {"status": "ok", "paper_order_submission_enabled": False}
