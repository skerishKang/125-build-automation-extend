"""Configuration helpers for the backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

# Load environment variables once at module import.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@dataclass(frozen=True)
class TelegramSettings:
    token: str
    app_name: Optional[str] = None


@dataclass(frozen=True)
class GmailSettings:
    monitor_interval: int = 300


@lru_cache(maxsize=1)
def get_telegram_settings() -> TelegramSettings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    app_name = os.getenv("TELEGRAM_APP_NAME")
    return TelegramSettings(token=token, app_name=app_name)


@lru_cache(maxsize=1)
def get_gmail_settings() -> GmailSettings:
    interval = int(os.getenv("GMAIL_MONITOR_INTERVAL", "300"))
    return GmailSettings(monitor_interval=interval)


__all__ = ["TelegramSettings", "GmailSettings", "get_telegram_settings", "get_gmail_settings"]
