from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("knowetrade.alerts")


def _alerts_enabled() -> bool:
    return os.getenv("SLACK_ALERTS_ENABLED", "true").strip().lower() == "true"


def _post_to_slack(text: str, blocks: list[dict[str, Any]] | None = None) -> None:
    if not _alerts_enabled():
        logger.info("slack.disabled_via_flag message=%s", text)
        return

    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        logger.info("slack.disabled message=%s", text)
        return

    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        response = httpx.post(webhook, json=payload, timeout=10)
        response.raise_for_status()
    except Exception:
        logger.exception("slack.send_failed")


def sendCriticalAlert(title: str, details: str) -> None:
    text = f":rotating_light: *CRITICAL* - {title}\n{details}"
    _post_to_slack(text=text)


def sendWarningAlert(title: str, details: str) -> None:
    text = f":warning: *WARNING* - {title}\n{details}"
    _post_to_slack(text=text)


def sendDailySummary(summary_lines: list[str]) -> None:
    if not summary_lines:
        summary_lines = ["No daily activity captured."]
    body = "\n".join(f"- {line}" for line in summary_lines)
    text = f":bar_chart: *Daily Summary*\n{body}"
    _post_to_slack(text=text)


def send_slack_alert(message: str) -> None:
    """Backwards-compatible generic alert helper."""
    _post_to_slack(text=message)
