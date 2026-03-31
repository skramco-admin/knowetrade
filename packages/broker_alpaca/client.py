from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any

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


class AlpacaBrokerClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.key_id = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_API_SECRET", "")
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
