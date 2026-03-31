from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("knowetrade.broker.alpaca")


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
        headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
        }
        response = httpx.post(f"{self.base_url}/v2/orders", json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        body = response.json()
        logger.info("broker.place_order.success id=%s", body.get("id"))
        return body
