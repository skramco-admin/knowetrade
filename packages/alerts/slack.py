from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("knowetrade.alerts")


def send_slack_alert(message: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        logger.info("slack.disabled message=%s", message)
        return

    try:
        response = httpx.post(webhook, json={"text": message}, timeout=10)
        response.raise_for_status()
    except Exception:
        logger.exception("slack.send_failed")
