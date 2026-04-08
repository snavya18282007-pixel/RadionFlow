from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings


class AutomationService:
    def __init__(self) -> None:
        self.webhook_url = get_settings().n8n_webhook_url

    def trigger_case_finalized(self, payload: dict[str, Any]) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()

        if not self.webhook_url:
            return {
                "triggered": False,
                "endpoint": None,
                "error": "N8N webhook URL is not configured.",
                "triggered_at": timestamp,
                "status_code": None,
            }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            response_preview = response.text.strip()
            if len(response_preview) > 500:
                response_preview = response_preview[:500] + "..."
            return {
                "triggered": True,
                "endpoint": self.webhook_url,
                "error": None,
                "triggered_at": timestamp,
                "status_code": response.status_code,
                "response_preview": response_preview or None,
            }
        except requests.RequestException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            return {
                "triggered": False,
                "endpoint": self.webhook_url,
                "error": str(exc),
                "triggered_at": timestamp,
                "status_code": status_code,
            }
