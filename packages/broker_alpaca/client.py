from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("knowetrade.broker.alpaca")


class BrokerAuthError(Exception):
    pass


class OrderRejectedError(Exception):
    pass


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    qty: int
    side: str


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    bar_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    qty: float


@dataclass(frozen=True)
class BrokerOrder:
    id: str
    symbol: str
    side: str
    qty: float
    status: str


class AlpacaBrokerClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.data_base_url = os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")
        self.key_id = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_API_SECRET", "") or os.getenv("ALPACA_SECRET_KEY", "")
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    def _auth_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    def validate_auth(self) -> None:
        if self.dry_run:
            logger.info("broker.auth_check.skipped dry_run=true")
            return
        if not self.key_id or not self.secret_key:
            raise BrokerAuthError("Missing Alpaca API credentials")
        try:
            response = httpx.get(
                f"{self.base_url}/v2/account",
                headers=self._auth_headers(),
                timeout=10,
            )
            if response.status_code in (401, 403):
                raise BrokerAuthError(f"Alpaca auth failed (status={response.status_code})")
            response.raise_for_status()
        except BrokerAuthError:
            raise
        except Exception as exc:
            raise BrokerAuthError(f"Alpaca auth check failed: {exc}") from exc

    def validate_auth_strict(self) -> None:
        self._ensure_credentials()
        try:
            response = httpx.get(
                f"{self.base_url}/v2/account",
                headers=self._auth_headers(),
                timeout=10,
            )
            if response.status_code in (401, 403):
                raise BrokerAuthError(f"Alpaca auth failed (status={response.status_code})")
            response.raise_for_status()
        except BrokerAuthError:
            raise
        except Exception as exc:
            raise BrokerAuthError(f"Alpaca auth check failed: {exc}") from exc

    def _ensure_credentials(self) -> None:
        if not self.key_id or not self.secret_key:
            raise BrokerAuthError("Missing Alpaca API credentials")

    def ensure_paper_trading(self) -> None:
        if "paper-api.alpaca.markets" not in self.base_url:
            raise BrokerAuthError("Order submission is allowed only to Alpaca paper endpoint")

    def place_order(self, order: OrderRequest) -> dict[str, Any]:
        logger.info("broker.place_order.start symbol=%s qty=%s", order.symbol, order.qty)

        if self.dry_run:
            simulated = {"id": f"dryrun-{uuid.uuid4()}", "status": "accepted"}
            logger.info("broker.place_order.dry_run id=%s", simulated["id"])
            return simulated

        payload = {
            "symbol": order.symbol,
            "qty": order.qty,
            "side": order.side,
            "type": "market",
            "time_in_force": "day",
        }
        response = httpx.post(f"{self.base_url}/v2/orders", json=payload, headers=self._auth_headers(), timeout=15)
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca order auth failure (status={response.status_code})")
        if 400 <= response.status_code < 500:
            raise OrderRejectedError(f"Order rejected status={response.status_code} body={response.text}")
        response.raise_for_status()
        body = response.json()
        logger.info("broker.place_order.success id=%s", body.get("id"))
        if body.get("status") in {"rejected", "canceled", "cancelled"}:
            raise OrderRejectedError(f"Order rejected by broker status={body.get('status')}")
        return body

    def submit_paper_order(self, order: OrderRequest) -> dict[str, Any]:
        self._ensure_credentials()
        self.ensure_paper_trading()
        return self.place_order(order)

    def get_position_qty(self, symbol: str) -> float:
        if self.dry_run:
            return 0.0
        response = httpx.get(
            f"{self.base_url}/v2/positions/{symbol.upper()}",
            headers=self._auth_headers(),
            timeout=10,
        )
        if response.status_code == 404:
            return 0.0
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca position auth failure (status={response.status_code})")
        response.raise_for_status()
        body = response.json()
        qty = body.get("qty", 0)
        try:
            return float(qty)
        except (TypeError, ValueError):
            return 0.0

    def list_positions(self) -> list[BrokerPosition]:
        self._ensure_credentials()
        response = httpx.get(
            f"{self.base_url}/v2/positions",
            headers=self._auth_headers(),
            timeout=15,
        )
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca positions auth failure (status={response.status_code})")
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            return []
        out: list[BrokerPosition] = []
        for row in body:
            try:
                qty = float(row.get("qty", 0))
            except (TypeError, ValueError):
                qty = 0.0
            symbol = str(row.get("symbol", "")).upper()
            if not symbol:
                continue
            out.append(BrokerPosition(symbol=symbol, qty=qty))
        return out

    def list_open_orders(self) -> list[BrokerOrder]:
        self._ensure_credentials()
        response = httpx.get(
            f"{self.base_url}/v2/orders?status=open&direction=desc&limit=500",
            headers=self._auth_headers(),
            timeout=15,
        )
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca open-orders auth failure (status={response.status_code})")
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            return []
        out: list[BrokerOrder] = []
        for row in body:
            try:
                qty = float(row.get("qty", 0))
            except (TypeError, ValueError):
                qty = 0.0
            out.append(
                BrokerOrder(
                    id=str(row.get("id", "")),
                    symbol=str(row.get("symbol", "")).upper(),
                    side=str(row.get("side", "")).lower(),
                    qty=qty,
                    status=str(row.get("status", "")).lower(),
                )
            )
        return out

    def has_open_order(self, symbol: str) -> bool:
        if self.dry_run:
            return False
        query = urlencode(
            {
                "status": "open",
                "symbols": symbol.upper(),
                "direction": "desc",
                "limit": "1",
            }
        )
        response = httpx.get(
            f"{self.base_url}/v2/orders?{query}",
            headers=self._auth_headers(),
            timeout=10,
        )
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca order-list auth failure (status={response.status_code})")
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            return False
        return any(str(order.get("symbol", "")).upper() == symbol.upper() for order in body)

    def get_latest_daily_bar(self, symbol: str) -> DailyBar | None:
        self._ensure_credentials()
        query = urlencode(
            {
                "timeframe": "1Day",
                "limit": "1",
                "adjustment": "raw",
                "feed": "iex",
            }
        )
        response = httpx.get(
            f"{self.data_base_url}/v2/stocks/{symbol.upper()}/bars?{query}",
            headers=self._auth_headers(),
            timeout=20,
        )
        if response.status_code in (401, 403):
            raise BrokerAuthError(f"Alpaca bars auth failure (status={response.status_code})")
        response.raise_for_status()
        body = response.json()
        entries = body.get("bars", [])
        if not entries:
            return None

        latest = entries[-1]
        bar_time_raw = latest.get("t")
        if not isinstance(bar_time_raw, str):
            return None
        bar_time = datetime.fromisoformat(bar_time_raw.replace("Z", "+00:00"))
        try:
            return DailyBar(
                symbol=symbol.upper(),
                bar_time=bar_time,
                open=float(latest.get("o")),
                high=float(latest.get("h")),
                low=float(latest.get("l")),
                close=float(latest.get("c")),
                volume=int(latest.get("v", 0)),
            )
        except (TypeError, ValueError):
            return None
